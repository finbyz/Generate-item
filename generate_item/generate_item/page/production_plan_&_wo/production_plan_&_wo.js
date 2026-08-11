const PPWO_API = "generate_item.generate_item.page.production_plan_&_wo.production_plan_&_wo";

frappe.pages["production-plan-&-wo"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: "Production Plan & Work Order Update Control Report",
		single_column: true,
	});
	frappe.ppwo_control_report = new PPWOControlReport(wrapper);
};

class PPWOControlReport {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = wrapper.page;
		this.$body = $(wrapper).find(".layout-main-section");
		this.$body.empty().addClass("ppwo-root");

		this.state = {
			theme: localStorage.getItem("ppwo_theme") || "light",
			filters: {},
			rows: [],
			total: 0,
			start: 0,
			page_length: 50,
			loading: false,
			selected: new Set(),
			cache: {},
			last_kpis: null,
			kpi_filter: null,
			drawer_open: false,
		};

		this.resize_observer = null;
		this.inject_styles();
		this.build_layout();
		// this.bind_page_actions();
		this.load_filter_options().then(() => this.refresh_all());
		this.setup_responsive_handling();
	}

	// ------------------------------------------------------------------ //
	// Responsive Handling
	// ------------------------------------------------------------------ //
	setup_responsive_handling() {
		let resize_timeout;
		const handle_resize = () => {
			clearTimeout(resize_timeout);
			resize_timeout = setTimeout(() => {
				this.update_chart_dimensions();
				this.adjust_grid_columns();
			}, 250);
		};

		window.addEventListener('resize', handle_resize);
		
		$(document).on('pagehide', () => {
			window.removeEventListener('resize', handle_resize);
			if (this.resize_observer) {
				this.resize_observer.disconnect();
			}
		});

		if (window.ResizeObserver) {
			this.resize_observer = new ResizeObserver(() => {
				clearTimeout(resize_timeout);
				resize_timeout = setTimeout(() => {
					this.update_chart_dimensions();
				}, 300);
			});
			this.resize_observer.observe(this.$body[0]);
		}
	}

	update_chart_dimensions() {
		const width = this.$body.width();
		const is_mobile = width < 768;
		const is_tablet = width >= 768 && width < 1024;

		$('.ppwo-chart-card').each((i, el) => {
			const $card = $(el);
			const canvas = $card.find('canvas');
			if (canvas.length) {
				const height = is_mobile ? 150 : is_tablet ? 180 : 200;
				canvas.attr('height', height);
				canvas.css('height', height + 'px');
			}
		});
	}

	adjust_grid_columns() {
		const width = this.$body.width();
		const $table = this.$body.find('table.ppwo-grid');
		
		if (width < 640) {
			$table.find('thead th').each((i, th) => {
				const $th = $(th);
				const col_idx = i;
				if ([2, 4, 6, 8, 10, 12, 14, 16, 17, 18].includes(col_idx)) {
					$th.css('display', 'none');
					$table.find(`tbody tr td:nth-child(${col_idx + 1})`).css('display', 'none');
				} else {
					$th.css('display', '');
					$table.find(`tbody tr td:nth-child(${col_idx + 1})`).css('display', '');
				}
			});
		} else if (width < 1024) {
			$table.find('thead th').each((i, th) => {
				const $th = $(th);
				const col_idx = i;
				if ([4, 6, 8, 12, 14, 16, 17, 18].includes(col_idx)) {
					$th.css('display', 'none');
					$table.find(`tbody tr td:nth-child(${col_idx + 1})`).css('display', 'none');
				} else {
					$th.css('display', '');
					$table.find(`tbody tr td:nth-child(${col_idx + 1})`).css('display', '');
				}
			});
		} else {
			$table.find('thead th').css('display', '');
			$table.find('tbody tr td').css('display', '');
		}
	}

	// ------------------------------------------------------------------ //
	// Styles
	// ------------------------------------------------------------------ //
	inject_styles() {
		if (document.getElementById("ppwo-styles")) return;
		const css = `
		:root[data-ppwo-theme="light"]{
			--ppwo-bg:#F7F9FC; --ppwo-bg-2:#EEF3FA;
			--ppwo-surface:rgba(255,255,255,0.72); --ppwo-surface-solid:#FFFFFF;
			--ppwo-border:rgba(24,39,75,0.08); --ppwo-text:#1C2C4C; --ppwo-text-dim:#6B7A99;
			--ppwo-shadow:0 8px 30px rgba(28,44,76,0.07);
		}
		:root[data-ppwo-theme="dark"]{
			--ppwo-bg:#0E1420; --ppwo-bg-2:#131A28;
			--ppwo-surface:rgba(23,30,44,0.62); --ppwo-surface-solid:#182233;
			--ppwo-border:rgba(255,255,255,0.08); --ppwo-text:#E7ECF6; --ppwo-text-dim:#93A0BC;
			--ppwo-shadow:0 8px 30px rgba(0,0,0,0.45);
		}
		:root{
			--ppwo-primary:#2490EF; --ppwo-primary-2:#7CB9F0;
			--ppwo-green:#5EBB63; --ppwo-amber:#F5A623; --ppwo-red:#E86161; --ppwo-blue:#4C9CE2; --ppwo-grey:#98A6BF;
			--ppwo-radius:16px; --ppwo-radius-sm:10px;
			--ppwo-font-display:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
			--ppwo-font-body:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
			--ppwo-font-mono:ui-monospace,SFMono-Regular,'SF Mono',Consolas,'Liberation Mono',Menlo,monospace;
		}
		@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
		
		.ppwo-root{background:radial-gradient(1200px 600px at 10% -10%, rgba(36,144,239,0.08), transparent),
			radial-gradient(1000px 500px at 100% 0%, rgba(124,185,240,0.10), transparent), var(--ppwo-bg);
			font-family:var(--ppwo-font-body); color:var(--ppwo-text); min-height:100vh; padding:0 4px 40px;
			transition:background .3s ease,color .3s ease;
			overflow:visible;}
		.ppwo-root *{box-sizing:border-box;}
		.ppwo-glass{background:var(--ppwo-surface); backdrop-filter:blur(16px) saturate(140%); -webkit-backdrop-filter:blur(16px) saturate(140%);
			border:1px solid var(--ppwo-border); border-radius:var(--ppwo-radius); box-shadow:var(--ppwo-shadow);}
		
		/* ================================================================= */
		/* FIX: Filter bar z-index & overflow — dropdowns must not be clipped */
		/* ================================================================= */
		.ppwo-filterbar{
			top:0;
			display:grid; grid-template-columns:repeat(4, 1fr);
			gap:10px; align-items:end;
			padding:14px 16px; margin:14px 0 18px;
			background:var(--ppwo-surface);
			backdrop-filter:blur(16px) saturate(140%);
			-webkit-backdrop-filter:blur(16px) saturate(140%);
			position:relative;
			z-index:100;
			overflow:visible !important;
			isolation:isolate;
		}
	
		/* Ensure no parent in Frappe's page layout clips the dropdown */
		.layout-main-section,
		.layout-main-section > .ppwo-root,
		.layout-main-wrapper {
			overflow:visible !important;
		}
	
		/* Boost Frappe's autocomplete dropdown above all our glass surfaces */
		.frappe-autocomplete,
		body > .frappe-autocomplete,
		.ui-autocomplete {
			z-index:10000 !important;
		}
		/* ================================================================= */
	
		.ppwo-filterbar .ppwo-field{min-width:0; width:100%; overflow:visible;}
		.ppwo-filterbar .ppwo-field label{font-size:11px; text-transform:uppercase; letter-spacing:.05em;
			color:var(--ppwo-text-dim); font-weight:600; margin-bottom:3px; display:block;}
		.ppwo-filterbar .ppwo-field .form-control{width:100%;}
		
		.ppwo-filterbar .ppwo-date-range-wrap{grid-column:span 2;}
		
		.ppwo-filterbar .ppwo-toggle-pills-wrap{
			display:flex; gap:6px; align-items:center;
			justify-content:flex-start; flex-wrap:wrap;
			grid-column:span 1;
			padding-top:4px;
		}
		
		.ppwo-filterbar .ppwo-toggle-pills-wrap label{
			display:none;
		}
		
		.ppwo-toggle-pill{display:inline-flex; align-items:center; gap:6px;
			padding:6px 12px; border-radius:999px;
			border:1px solid var(--ppwo-border);
			background:var(--ppwo-surface-solid); cursor:pointer;
			font-size:12px; font-weight:600; color:var(--ppwo-text-dim);
			transition:all .18s; white-space:nowrap;
			height:32px;}
		.ppwo-toggle-pill.active{background:linear-gradient(135deg,var(--ppwo-primary),var(--ppwo-primary-2));
			color:#fff; border-color:transparent;
			box-shadow:0 4px 14px rgba(36,144,239,.35);}
		
		/* Responsive filter bar */
		@media (max-width:1200px){
			.ppwo-filterbar{grid-template-columns:repeat(4, 1fr);}
		}
		@media (max-width:992px){
			.ppwo-filterbar{grid-template-columns:repeat(3, 1fr);}
			.ppwo-filterbar .ppwo-date-range-wrap{grid-column:span 2;}
		}
		@media (max-width:768px){
			.ppwo-filterbar{grid-template-columns:repeat(2, 1fr); gap:8px; padding:12px 14px;}
			.ppwo-filterbar .ppwo-date-range-wrap{grid-column:span 2;}
			.ppwo-filterbar .ppwo-toggle-pills-wrap{grid-column:span 2; justify-content:center;}
		}
		@media (max-width:480px){
			.ppwo-filterbar{grid-template-columns:1fr; gap:6px; padding:10px 12px;}
			.ppwo-filterbar .ppwo-date-range-wrap{grid-column:span 1;}
			.ppwo-filterbar .ppwo-toggle-pills-wrap{grid-column:span 1; justify-content:center;}
		}
		
		/* KPI Cards */
		.ppwo-kpi-row{display:grid; grid-template-columns:repeat(auto-fit, minmax(120px, 1fr)); gap:10px; margin-bottom:18px; min-height:82px;}
		@media (max-width:640px){.ppwo-kpi-row{grid-template-columns:repeat(3, 1fr); gap:6px;}}
		@media (max-width:480px){.ppwo-kpi-row{grid-template-columns:repeat(2, 1fr); gap:4px;}}
		
		.ppwo-kpi{padding:12px 10px; cursor:pointer; position:relative; overflow:hidden; transition:transform .18s ease,box-shadow .18s ease;}
		.ppwo-kpi:hover{transform:translateY(-2px); box-shadow:0 10px 24px rgba(20,22,35,.12);}
		.ppwo-kpi::after{content:''; position:absolute; inset:0; opacity:0; background:linear-gradient(120deg,transparent,rgba(255,255,255,.35),transparent);
			transform:translateX(-120%); transition:none;}
		.ppwo-kpi.active{outline:2px solid var(--ppwo-primary);}
		.ppwo-kpi .ppwo-kpi-label{font-size:10px; color:var(--ppwo-text-dim); font-weight:600; text-transform:uppercase; letter-spacing:.03em;}
		.ppwo-kpi .ppwo-kpi-value{font-family:var(--ppwo-font-mono); font-size:24px; font-weight:600; margin-top:4px; line-height:1;}
		.ppwo-kpi .ppwo-kpi-bar{height:2px; border-radius:2px; margin-top:8px; background:var(--ppwo-border); overflow:hidden;}
		.ppwo-kpi .ppwo-kpi-bar span{display:block; height:100%; border-radius:2px; transition:width .8s cubic-bezier(.22,1,.36,1);}
		
		/* Progress */
		.ppwo-progress-row{display:flex; align-items:center; gap:16px; padding:14px 18px; margin-bottom:18px;}
		.ppwo-ring{width:52px; height:52px; flex-shrink:0;}
		.ppwo-ring circle.bg{stroke:var(--ppwo-border); fill:none; stroke-width:6;}
		.ppwo-ring circle.fg{stroke:var(--ppwo-primary); fill:none; stroke-width:6; stroke-linecap:round;
			transition:stroke-dashoffset 1s cubic-bezier(.22,1,.36,1);}
		.ppwo-ring text{font-family:var(--ppwo-font-mono); font-size:13px; fill:var(--ppwo-text); font-weight:600;}
		.ppwo-progress-bar-outer{flex:1; height:6px; border-radius:6px; background:var(--ppwo-border); overflow:hidden;}
		.ppwo-progress-bar-inner{height:100%; border-radius:6px; background:linear-gradient(90deg,var(--ppwo-primary),var(--ppwo-primary-2));
			transition:width 1s cubic-bezier(.22,1,.36,1); box-shadow:0 0 12px rgba(36,144,239,.5);}
		
		/* Grid */
		.ppwo-grid-wrap{overflow:auto; max-height:66vh; border-radius:var(--ppwo-radius); position:relative;}
		table.ppwo-grid{width:100%; border-collapse:separate; border-spacing:0; font-size:12px; table-layout:auto;}
		table.ppwo-grid thead th{position:sticky; top:0; background:var(--ppwo-surface-solid); z-index:5; text-align:left; padding:9px 10px;
			font-size:10px; text-transform:uppercase; letter-spacing:.04em; color:var(--ppwo-text-dim); font-weight:700;
			border-bottom:2px solid var(--ppwo-border); white-space:nowrap; box-shadow:0 1px 0 rgba(36,144,239,.15);}
		table.ppwo-grid td{padding:7px 10px; border-bottom:1px solid var(--ppwo-border); white-space:nowrap; vertical-align:middle;
			max-width:180px; overflow:hidden; text-overflow:ellipsis;}
		
		/* Charts - 2x2 Grid */
		.ppwo-charts-row{display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:16px;}
		.ppwo-chart-card{padding:14px 16px; min-height:220px;}
		.ppwo-chart-card h4{font-family:var(--ppwo-font-display); font-size:13px; margin:0 0 10px; font-weight:600;}
		.ppwo-chart-card canvas{width:100% !important; height:auto !important; max-height:200px;}
		
		.ppwo-chart-card.full-width{grid-column:1/-1;}
		
		@media (max-width:1024px){
			.ppwo-charts-row{grid-template-columns:1fr 1fr; gap:12px;}
		}
		@media (max-width:768px){
			.ppwo-charts-row{grid-template-columns:1fr 1fr; gap:10px;}
			.ppwo-chart-card{min-height:200px; padding:12px 14px;}
		}
		@media (max-width:480px){
			.ppwo-charts-row{grid-template-columns:1fr; gap:10px;}
			.ppwo-chart-card{min-height:180px; padding:10px 12px;}
			.ppwo-chart-card.full-width{grid-column:1;}
		}
		
		/* Branch Performance */
		.ppwo-branch-perf-item{display:flex; align-items:center; gap:8px; margin-bottom:6px; font-size:11.5px;}
		.ppwo-branch-perf-item .branch-name{width:100px; flex-shrink:0; overflow:hidden; text-overflow:ellipsis; font-weight:500;}
		.ppwo-branch-perf-item .branch-bar{flex:1; height:6px; border-radius:6px; background:var(--ppwo-border); overflow:hidden;}
		.ppwo-branch-perf-item .branch-bar-inner{height:100%; border-radius:6px; background:linear-gradient(90deg,var(--ppwo-primary),var(--ppwo-primary-2));
			transition:width 1s cubic-bezier(.22,1,.36,1);}
		.ppwo-branch-perf-item .branch-pct{width:55px; text-align:right; font-family:var(--ppwo-font-mono); font-size:11px; flex-shrink:0; font-weight:600;}
		.ppwo-branch-perf-item .branch-count{width:80px; color:var(--ppwo-text-dim); font-size:10px; flex-shrink:0; text-align:right;}
		
		@media (max-width:480px){
			.ppwo-branch-perf-item .branch-name{width:70px; font-size:10px;}
			.ppwo-branch-perf-item .branch-pct{width:45px; font-size:10px;}
			.ppwo-branch-perf-item .branch-count{width:60px; font-size:9px;}
		}
		
		/* Other styles */
		.ppwo-mono{font-family:var(--ppwo-font-mono); font-size:11px;}
		.ppwo-badge{display:inline-flex; align-items:center; gap:3px; padding:2px 7px; border-radius:999px; font-size:10px; font-weight:600; white-space:nowrap;}
		.ppwo-chip-btn{display:inline-flex; align-items:center; gap:4px; padding:3px 8px; border-radius:999px; font-size:11px; font-weight:600;
			font-family:var(--ppwo-font-mono); border:1px solid var(--ppwo-border); background:var(--ppwo-surface-solid); color:var(--ppwo-primary);
			cursor:pointer; transition:all .15s;}
		.ppwo-chip-btn:hover{background:var(--ppwo-primary); color:#fff; border-color:transparent; box-shadow:0 4px 12px rgba(36,144,239,.35);}
		.ppwo-chip-btn .arrow{opacity:.6; font-size:9px;}
		.ppwo-cell-link{font-family:var(--ppwo-font-mono); font-size:11px; color:var(--ppwo-primary); cursor:pointer; text-decoration:none;}
		.ppwo-cell-link:hover{text-decoration:underline;}
		.ppwo-dash{color:var(--ppwo-text-dim); opacity:.5;}
		.ppwo-badge.updated{background:rgba(16,185,129,.12); color:var(--ppwo-green);}
		.ppwo-badge.pending{background:rgba(245,158,11,.14); color:var(--ppwo-amber);}
		.ppwo-badge.critical{background:rgba(239,68,68,.14); color:var(--ppwo-red);}
		.ppwo-badge.not_required{background:rgba(59,130,246,.12); color:var(--ppwo-blue);}
		.ppwo-badge.waiting{background:rgba(138,143,156,.14); color:var(--ppwo-grey);}
		.ppwo-sev{font-weight:700; font-size:10px; padding:2px 8px; border-radius:999px;}
		.ppwo-sev.Critical{background:var(--ppwo-red); color:#fff;}
		.ppwo-sev.High{background:var(--ppwo-amber); color:#1a1300;}
		.ppwo-sev.Medium{background:var(--ppwo-blue); color:#fff;}
		.ppwo-sev.Waiting{background:var(--ppwo-grey); color:#fff;}
		.ppwo-sev.Low{background:var(--ppwo-green); color:#fff;}
		
		.ppwo-rail{display:flex; align-items:center; gap:2px;}
		.ppwo-rail .seg{width:16px; height:3px; border-radius:2px; background:var(--ppwo-border); position:relative;}
		.ppwo-rail .seg.completed{background:var(--ppwo-green);}
		.ppwo-rail .seg.pending{background:var(--ppwo-amber);}
		.ppwo-rail .seg.blocked{background:var(--ppwo-red);}
		.ppwo-rail .seg.not_required{background:var(--ppwo-blue); opacity:.5;}
		.ppwo-rail .pulse{position:absolute; top:-2px; width:7px; height:7px; border-radius:50%; background:var(--ppwo-primary);
			box-shadow:0 0 8px 2px rgba(36,144,239,.7); animation:ppwo-pulse-move 2.6s ease-in-out infinite;}
		.ppwo-rail .seg.blocked .pulse{background:var(--ppwo-red); box-shadow:0 0 10px 3px rgba(239,68,68,.8); animation:ppwo-pulse-stall 1s ease-in-out infinite;}
		@keyframes ppwo-pulse-move{0%{left:0;}50%{left:10px;}100%{left:0;}}
		@keyframes ppwo-pulse-stall{0%,100%{transform:scale(1);}50%{transform:scale(1.6);}}
		
		.ppwo-skel{background:linear-gradient(90deg,var(--ppwo-border) 25%,rgba(255,255,255,.35) 50%,var(--ppwo-border) 75%);
			background-size:200% 100%; animation:ppwo-shimmer 1.3s linear infinite; border-radius:6px;}
		@keyframes ppwo-shimmer{0%{background-position:200% 0;}100%{background-position:-200% 0;}}
		
		.ppwo-drawer-overlay{position:fixed; inset:0; background:rgba(10,10,15,.35); backdrop-filter:blur(2px); z-index:100; opacity:0;
			pointer-events:none; transition:opacity .25s;}
		.ppwo-drawer-overlay.open{opacity:1; pointer-events:all;}
		.ppwo-drawer{position:fixed; top:0; right:0; height:100vh; width:min(480px,92vw); background:var(--ppwo-surface-solid); z-index:101;
			box-shadow:-14px 0 40px rgba(0,0,0,.25); transform:translateX(100%); transition:transform .32s cubic-bezier(.22,1,.36,1);
			overflow-y:auto; padding:20px;}
		.ppwo-drawer.open{transform:translateX(0);}
		.ppwo-drawer h3{font-family:var(--ppwo-font-display); margin:0 0 4px; font-size:18px;}
		.ppwo-drawer .close-btn{position:absolute; top:16px; right:16px; cursor:pointer; font-size:20px; opacity:.6; padding:4px 8px;}
		.ppwo-drawer .section-title{font-size:10px; text-transform:uppercase; letter-spacing:.05em; color:var(--ppwo-text-dim); font-weight:700; margin:14px 0 6px;}
		.ppwo-timeline-item{display:flex; gap:8px; padding:6px 0; border-bottom:1px dashed var(--ppwo-border); font-size:12px;}
		.ppwo-timeline-item .dot{width:6px; height:6px; border-radius:50%; background:var(--ppwo-primary); margin-top:4px; flex-shrink:0;}
		.ppwo-pending-action{display:flex; gap:6px; align-items:flex-start; padding:6px 10px; border-radius:8px; background:rgba(245,158,11,.08);
			margin-bottom:4px; font-size:12px;}
		
		.ppwo-accordion{margin-bottom:6px;}
		.ppwo-accordion-toggle{display:flex; justify-content:space-between; align-items:center; padding:8px 12px;
			background:rgba(36,144,239,0.04); border-radius:8px; cursor:pointer; font-weight:600; font-size:12px;
			border:1px solid var(--ppwo-border); transition:all 0.2s;}
		.ppwo-accordion-toggle:hover{background:rgba(36,144,239,0.08);}
		.ppwo-accordion-toggle .ppwo-accordion-arrow{font-size:9px; transition:transform 0.3s ease; display:inline-block;}
		.ppwo-accordion-toggle.active .ppwo-accordion-arrow{transform:rotate(180deg);}
		.ppwo-accordion-content{display:none; padding:6px 10px;}
		.ppwo-accordion-content .ppwo-doc-row{display:flex; justify-content:space-between; align-items:center;
			padding:5px 0; border-bottom:1px dashed var(--ppwo-border); font-size:11px;}
		.ppwo-accordion-content .ppwo-doc-row:last-child{border-bottom:none;}
		
		.ppwo-toolbar{display:flex; justify-content:space-between; align-items:center; padding:8px 14px; margin-bottom:10px; flex-wrap:wrap; gap:8px;}
		.ppwo-btn{border:1px solid var(--ppwo-border); background:var(--ppwo-surface-solid); border-radius:var(--ppwo-radius-sm); padding:6px 12px;
			font-size:12px; font-weight:600; cursor:pointer; position:relative; overflow:hidden; color:var(--ppwo-text);}
		.ppwo-btn.primary{background:linear-gradient(135deg,var(--ppwo-primary),var(--ppwo-primary-2)); color:#fff; border-color:transparent;}
		.ppwo-btn.primary:hover{opacity:0.9;}
		.ppwo-btn:hover{background:rgba(36,144,239,0.08);}
		.ppwo-ripple{position:absolute; border-radius:50%; background:rgba(255,255,255,.55); transform:scale(0); animation:ppwo-ripple-anim .55s ease-out;}
		@keyframes ppwo-ripple-anim{to{transform:scale(3.2); opacity:0;}}
		
		#ppwo-confetti-canvas{position:fixed; inset:0; z-index:9999; pointer-events:none;}
		
		table.ppwo-grid tbody tr{cursor:pointer; transition:background .12s;}
		table.ppwo-grid tbody tr:nth-child(even){background:rgba(36,144,239,0.025);}
		table.ppwo-grid tbody tr:hover{background:rgba(36,144,239,.09);}
		table.ppwo-grid tbody tr.ppwo-row-critical{box-shadow:inset 3px 0 0 var(--ppwo-red);}
		table.ppwo-grid tbody tr.ppwo-row-high{box-shadow:inset 3px 0 0 var(--ppwo-amber);}
		table.ppwo-grid tbody tr.ppwo-row-medium{box-shadow:inset 3px 0 0 var(--ppwo-blue);}
		table.ppwo-grid tbody tr.ppwo-row-waiting{box-shadow:inset 3px 0 0 var(--ppwo-grey);}
	
		`;
		const style = document.createElement("style");
		style.id = "ppwo-styles";
		style.textContent = css;
		document.head.appendChild(style);
		document.documentElement.setAttribute("data-ppwo-theme", this.state.theme);
	}

	// ------------------------------------------------------------------ //
	// Layout
	// ------------------------------------------------------------------ //
	build_layout() {
		this.$body.html(`
			<div class="ppwo-filterbar ppwo-glass"></div>
			<div class="ppwo-kpi-row"></div>
			<div class="ppwo-progress-row ppwo-glass">
				<svg class="ppwo-ring" viewBox="0 0 64 64">
					<circle class="bg" cx="32" cy="32" r="26"></circle>
					<circle class="fg" cx="32" cy="32" r="26" stroke-dasharray="163.4" stroke-dashoffset="163.4" transform="rotate(-90 32 32)"></circle>
					<text x="32" y="37" text-anchor="middle">0%</text>
				</svg>
				<div style="flex:1">
					<div style="font-size:12px;color:var(--ppwo-text-dim);font-weight:600;margin-bottom:6px;">OVERALL SYNCHRONIZATION</div>
					<div class="ppwo-progress-bar-outer"><div class="ppwo-progress-bar-inner" style="width:0%"></div></div>
				</div>
			</div>
			<div class="ppwo-toolbar ppwo-glass">
				<div class="ppwo-toolbar-left" style="font-size:12.5px;color:var(--ppwo-text-dim);font-weight:600;"></div>
				<div class="ppwo-toolbar-right" style="display:flex;gap:8px;"></div>
			</div>
			<div class="ppwo-grid-wrap ppwo-glass"><table class="ppwo-grid"><thead></thead><tbody></tbody></table></div>
			<div id="ppwo-load-more" style="text-align:center;padding:14px;font-size:12px;color:var(--ppwo-text-dim);cursor:pointer;">Load more rows</div>
			<div class="ppwo-charts-row">
				<div class="ppwo-chart-card ppwo-glass"><h4>Pending Updates by Branch</h4><div class="c-branch"></div></div>
				<div class="ppwo-chart-card ppwo-glass"><h4>Status Distribution</h4><div class="c-status"></div></div>
				<div class="ppwo-chart-card ppwo-glass"><h4>Manufacturing Funnel</h4><div class="c-funnel"></div></div>
				<div class="ppwo-chart-card ppwo-glass"><h4>30-Day Pending Trend</h4><div class="c-trend"></div></div>
				<div class="ppwo-chart-card ppwo-glass full-width"><h4>Branch Performance</h4><div class="c-branch-perf"></div></div>
			</div>
			<div class="ppwo-drawer-overlay"></div>
			<div class="ppwo-drawer ppwo-glass"><span class="close-btn">&times;</span><div class="ppwo-drawer-content"></div></div>
		`);
		this.build_filterbar();
		this.build_kpis();
		this.build_toolbar();
		this.build_grid_head();
		this.bind_grid_events();
		this.bind_drawer_events();
	}

	bind_page_actions() {
		this.page.set_secondary_action(
			this.state.theme === "dark" ? "☀️ Light" : "🌙 Dark",
			() => this.toggle_theme(),
			null
		);
	}

	toggle_theme() {
		this.state.theme = this.state.theme === "dark" ? "light" : "dark";
		localStorage.setItem("ppwo_theme", this.state.theme);
		document.documentElement.setAttribute("data-ppwo-theme", this.state.theme);
		this.page.set_secondary_action(this.state.theme === "dark" ? "☀️ Light" : "🌙 Dark", () => this.toggle_theme());
	}

	ripple(el, ev) {
		const r = document.createElement("span");
		r.className = "ppwo-ripple";
		const rect = el.getBoundingClientRect();
		r.style.left = (ev.clientX - rect.left - 8) + "px";
		r.style.top = (ev.clientY - rect.top - 8) + "px";
		r.style.width = r.style.height = "16px";
		el.appendChild(r);
		setTimeout(() => r.remove(), 550);
	}

	// ------------------------------------------------------------------ //
	// Filter bar
	// ------------------------------------------------------------------ //
	build_filterbar() {
		const $bar = this.$body.find(".ppwo-filterbar");
		const link_field = (label, fieldname, doctype) => `
			<div class="ppwo-field" data-fieldname="${fieldname}">
				<label>${label}</label>
				<div class="ppwo-link-target" data-doctype="${doctype}"></div>
			</div>`;
		
		$bar.html(`
			${link_field("Company", "company", "Company")}
			${link_field("Branch", "branch", "Branch")}
			${link_field("Sales Order", "sales_order", "Sales Order")}
			${link_field("OMR", "omr", "Order Modification Request")}
			${link_field("BMR", "bmr", "Bom Modification Request")}
			${link_field("Work Order", "work_order", "Work Order")}
			${link_field("Production Plan", "production_plan", "Production Plan")}
			
			${link_field("Customer", "customer", "Customer")}
			<div class="ppwo-field">
				<label>Date Period</label>
				<select class="form-control period-select">
					
					<option value="today" selected >Today</option>
					<option value="this_week">This Week</option>
					<option value="last_week">Last Week</option>
					<option value="this_month">This Month</option>
					<option value="last_month">Last Month</option>
					<option value="this_year">This Year</option>
					<option value="last_year">Last Year</option>
					<option value="custom">Custom…</option>
				</select>
			</div>
			<div class="ppwo-field ppwo-date-range-wrap">
				<label>From - To</label>
				<div style="display:flex; gap:6px; align-items:center;">
					<input type="date" class="form-control date-from" style="flex:1;" readonly>
					<span style="color:var(--ppwo-text-dim); font-size:11px; flex:0 0 auto;">→</span>
					<input type="date" class="form-control date-to" style="flex:1;" readonly>
				</div>
			</div>
			<div class="ppwo-field ppwo-toggle-pills-wrap">
				<label>&nbsp;</label>
				<div style="display:flex;gap:6px;flex-wrap:wrap;">
					<div class="ppwo-toggle-pill" data-toggle="pending_only">🟡 Pending Only</div>
					<div class="ppwo-toggle-pill" data-toggle="critical_only">🔴 Critical Only</div>
				</div>
			</div>
		`);

		this.link_controls = {};
		$bar.find(".ppwo-link-target").each((i, el) => {
			const $el = $(el);
			const doctype = $el.data("doctype");
			const fieldname = $el.closest(".ppwo-field").data("fieldname");
			const ctrl = frappe.ui.form.make_control({
				parent: el,
				df: { fieldtype: "Link", options: doctype, fieldname, placeholder: doctype },
				render_input: true,
			});
			ctrl.$input.addClass("form-control");
			ctrl.df.onchange = () => this.on_filters_changed();
			this.link_controls[fieldname] = ctrl;
		});

		this.update_date_fields();
		
		$bar.on("change", ".period-select", (e) => {
			this.update_date_fields();
			this.on_filters_changed();
		});
		$bar.on("change", ".date-from, .date-to", () => this.on_filters_changed());
		$bar.on("click", ".ppwo-toggle-pill", (e) => {
			$(e.currentTarget).toggleClass("active");
			this.on_filters_changed();
		});
	}

	update_date_fields() {
		const period = this.$body.find(".period-select").val();
		const $from = this.$body.find(".date-from");
		const $to = this.$body.find(".date-to");
		
		if (period === "custom") {
			$from.prop("readonly", false);
			$to.prop("readonly", false);
		} else {
			$from.prop("readonly", true);
			$to.prop("readonly", true);
			
			const today = new Date();
			let from = null, to = null;
			
			switch(period) {
				case "today":
					from = to = today;
					break;
				case "this_week":
					from = new Date(today);
					from.setDate(today.getDate() - today.getDay() + 1);
					to = new Date(from);
					to.setDate(from.getDate() + 6);
					break;
				case "last_week":
					from = new Date(today);
					from.setDate(today.getDate() - today.getDay() - 6);
					to = new Date(from);
					to.setDate(from.getDate() + 6);
					break;
				case "this_month":
					from = new Date(today.getFullYear(), today.getMonth(), 1);
					to = new Date(today.getFullYear(), today.getMonth() + 1, 0);
					break;
				case "last_month":
					from = new Date(today.getFullYear(), today.getMonth() - 1, 1);
					to = new Date(today.getFullYear(), today.getMonth(), 0);
					break;
				case "this_year":
					from = new Date(today.getFullYear(), 0, 1);
					to = new Date(today.getFullYear(), 11, 31);
					break;
				case "last_year":
					from = new Date(today.getFullYear() - 1, 0, 1);
					to = new Date(today.getFullYear() - 1, 11, 31);
					break;
			}
			
			if (from) {
				$from.val(from.toISOString().split('T')[0]);
				$to.val(to.toISOString().split('T')[0]);
			} else {
				$from.val("");
				$to.val("");
			}
		}
	}

	load_filter_options() {
    return frappe.call({ method: `${PPWO_API}.get_filter_options` }).then((r) => {
        const d = r.message || {};
        this.$body.find(".date-from").val(d.default_from || "");
        this.$body.find(".date-to").val(d.default_to || "");
        this.update_date_fields();
        this.on_filters_changed();
    });
}

	collect_filters() {
		const f = {};
		Object.keys(this.link_controls || {}).forEach((k) => {
			const v = this.link_controls[k].get_value();
			if (v) f[k] = v;
		});
		const period = this.$body.find(".period-select").val();
		if (period) {
			f.period = this.$body.find(".period-select").val() || "today";
			f.from_date = this.$body.find(".date-from").val();
			f.to_date = this.$body.find(".date-to").val();
		}
		f.pending_only = this.$body.find('.ppwo-toggle-pill[data-toggle="pending_only"]').hasClass("active") ? 1 : 0;
		f.critical_only = this.$body.find('.ppwo-toggle-pill[data-toggle="critical_only"]').hasClass("active") ? 1 : 0;
		if (this.state.kpi_filter) f[this.state.kpi_filter.type] = this.state.kpi_filter.value;
		return f;
	}

	on_filters_changed() {
		this.state.filters = this.collect_filters();
		this.state.start = 0;
		this.state.cache = {};
		this.state.selected.clear(); // ADD THIS LINE
		this.refresh_all();
	}

	// ------------------------------------------------------------------ //
	// KPI cards
	// ------------------------------------------------------------------ //
	build_kpis() {
		const defs = [
			{ key: "pending_pp", label: "Pending PP Updates", color: "var(--ppwo-red)" },
			{ key: "pending_wo", label: "Pending WO Updates", color: "var(--ppwo-amber)" },
			{ key: "pending_bmr", label: "Pending BMR", color: "var(--ppwo-blue)" },
			{ key: "pending_omr", label: "Pending OMR", color: "var(--ppwo-grey)" },
			{ key: "completed", label: "Completed Updates", color: "var(--ppwo-green)" },
			{ key: "critical", label: "Critical Pending", color: "var(--ppwo-red)" },
		];
		const $row = this.$body.find(".ppwo-kpi-row");
		$row.html(
			defs
				.map(
					(d) => `
			<div class="ppwo-kpi ppwo-glass" data-key="${d.key}">
				<div class="ppwo-kpi-label">${d.label}</div>
				<div class="ppwo-kpi-value" data-value="0">0</div>
				<div class="ppwo-kpi-bar"><span style="background:${d.color};width:0%"></span></div>
			</div>`
				)
				.join("")
		);
		this.kpi_defs = defs;
		$row.on("click", ".ppwo-kpi", (e) => {
			this.ripple(e.currentTarget, e);
			const key = $(e.currentTarget).data("key");
			const already_active = $(e.currentTarget).hasClass("active");
			$row.find(".ppwo-kpi").removeClass("active");
			if (already_active) {
				this.state.kpi_filter = null;
			} else {
				$(e.currentTarget).addClass("active");
				this.apply_kpi_shortcut(key);
			}
			this.on_filters_changed();
		});
	}

	apply_kpi_shortcut(key) {
		const map = {
			pending_pp: { type: "priority", value: "Critical" },
			critical: { type: "priority", value: "Critical" },
			pending_wo: { type: "priority", value: "High" },
			pending_bmr: { type: "priority", value: "Medium" },
			pending_omr: { type: "priority", value: "Waiting" },
			completed: { type: "status", value: "Fully Synced" },
		};
		this.state.kpi_filter = map[key] || null;
	}

	animate_count(el, target) {
		const $el = $(el);
		const start = parseInt($el.attr("data-value")) || 0;
		const dur = 700;
		const t0 = performance.now();
		const step = (now) => {
			const p = Math.min(1, (now - t0) / dur);
			const eased = 1 - Math.pow(1 - p, 3);
			const val = Math.round(start + (target - start) * eased);
			$el.text(val.toLocaleString());
			if (p < 1) requestAnimationFrame(step);
			else $el.attr("data-value", target);
		};
		requestAnimationFrame(step);
	}

	render_kpis(k) {
		if (!k) return;
		const max = Math.max(k.pending_pp, k.pending_wo, k.pending_bmr, k.pending_omr, k.completed, k.critical, 1);
		this.kpi_defs.forEach((d) => {
			const $card = this.$body.find(`.ppwo-kpi[data-key="${d.key}"]`);
			this.animate_count($card.find(".ppwo-kpi-value")[0], k[d.key] || 0);
			$card.find(".ppwo-kpi-bar span").css("width", `${((k[d.key] || 0) / max) * 100}%`);
		});
		const ring_fg = this.$body.find(".ppwo-ring circle.fg");
		const ring_text = this.$body.find(".ppwo-ring text");
		const circumference = 2 * Math.PI * 26;
		const pct = k.sync_pct || 0;
		ring_fg.attr("stroke-dashoffset", circumference - (circumference * pct) / 100);
		ring_text.text(`${Math.round(pct)}%`);
		this.$body.find(".ppwo-progress-bar-inner").css("width", `${pct}%`);
		this.state.total = k.total;
		const filter_note = this.state.kpi_filter ? ` · filtered by ${this.state.kpi_filter.type}: ${this.state.kpi_filter.value} (click card again to clear)` : "";
		this.$body.find(".ppwo-toolbar-left").text(`${k.total} sales orders in scope · ${k.trackable} being tracked${filter_note}`);

		const was_clear = this.state.last_kpis && this.state.last_kpis.all_clear;
		if (k.all_clear && !was_clear) this.celebrate();
		this.state.last_kpis = k;
	}

	// ------------------------------------------------------------------ //
	// Toolbar
	// ------------------------------------------------------------------ //
	build_toolbar() {
		const $right = this.$body.find(".ppwo-toolbar-right");
		
		$right.html(`
			<button class="ppwo-btn" data-act="refresh">↻ Refresh</button>
			
			<button class="ppwo-btn" data-act="export">⇩ Export All</button>
			<button class="ppwo-btn" data-act="export_selected" style="display:none;">⇩ Export Selected (0)</button>
		
			
		`);
		$right.on("click", ".ppwo-btn", (e) => {
			this.ripple(e.currentTarget, e);
			const act = $(e.currentTarget).data("act");
			if (act === "refresh") this.refresh_all(true);
			if (act === "export") this.export_csv();
			
		});
		// ADD these handlers in build_toolbar after the existing click handler:
		$right.on("click", ".ppwo-btn[data-act='export_selected']", (e) => {
			this.ripple(e.currentTarget, e);
			this.export_selected_csv();
		});
	}

	// REPLACE the entire export_csv function:
// export_csv() {
//     // Always export all filtered rows via server
//     const params = new URLSearchParams({
//         cmd: `${PPWO_API}.export_csv`,
//         filters: JSON.stringify(this.state.filters),
//     });
//     window.open(`/api/method/${PPWO_API}.export_csv?${params.toString()}`, "_blank");
// }

// // REPLACE the entire export_selected_csv function:
// export_selected_csv() {
//     if (this.state.selected.size === 0) {
//         frappe.msgprint(__("Please select at least one row to export."));
//         return;
//     }

//     const selected_rows = this.state.rows.filter(r => this.state.selected.has(r.sales_order));

//     if (selected_rows.length === 0) {
//         frappe.msgprint(__("No selected rows found in current view."));
//         return;
//     }

//     // Same column set as the server-side export_csv (Stage skipped, consistent order)
//     const columns = [
//         "Sales Order", "Customer", "OMR", "OMR Status",
//         "BMR", "BMR Status", "Production Plan",
//         "PP Update Req.", "PP Updated", "Work Order",
//         "WO Update Req.", "WO Updated",
//         "Pending At", "Severity", "Updated By", "Updated Time", "Remarks",
//     ];

//     let csv = columns.join(",") + "\r\n";

//     selected_rows.forEach(r => {
//         const bmr_names = (r.bmr_list || []).map(b => b.name);
//         const wo_names = (r.wo_list || []).map(w => w.name);

//         const vals = [
//             this._csv_value(this._clean(r.sales_order)),
//             this._csv_value(this._clean(r.customer_name)),
//             this._csv_value(this._clean(r.omr ? r.omr.name : "")),
//             this._csv_value(this._clean(r.omr_badge ? r.omr_badge.label : "")),
//             this._csv_value(this._clean(this._format_doc_list(bmr_names))),
//             this._csv_value(this._clean(r.bmr_badge ? r.bmr_badge.label : "")),
//             this._csv_value(this._clean(r.pp ? r.pp.name : "")),
//             this._csv_value(this._clean(r.pp_required_badge ? r.pp_required_badge.label : "")),
//             this._csv_value(this._clean(r.pp_updated_badge ? r.pp_updated_badge.label : "")),
//             this._csv_value(this._clean(this._format_doc_list(wo_names))),
//             this._csv_value(this._clean(r.wo_required_badge ? r.wo_required_badge.label : "")),
//             this._csv_value(this._clean(r.wo_updated_badge ? r.wo_updated_badge.label : "")),
//             this._csv_value(this._clean(r.pending_at)),
//             this._csv_value(this._clean(r.severity)),
//             this._csv_value(this._clean(r.modified_by)),
//             this._csv_value(this._clean(r.modified ? frappe.datetime.prettyDate(r.modified) : "")),   
//             this._csv_value(this._clean(r.is_pending ? ("Awaiting action at " + r.current_stage) : "")),
//         ];
//         csv += vals.join(",") + "\r\n";
//     });

//     // Prepend UTF-8 BOM so Excel opens it with correct encoding
//     const blob = new Blob(["\ufeff" + csv], { type: 'text/csv;charset=utf-8;' });
//     const link = document.createElement("a");
//     link.href = URL.createObjectURL(blob);
//     link.download = `production_plan_wo_selected_${frappe.datetime.now_date()}.csv`;
//     document.body.appendChild(link);
//     link.click();
//     document.body.removeChild(link);
//     URL.revokeObjectURL(link.href);

//     frappe.show_alert({
//         message: __("Exported {0} selected rows", [selected_rows.length]),
//         indicator: "green"
//     });
// }

export_csv() {
    const params = new URLSearchParams({
        cmd: `${PPWO_API}.export_excel`,
        filters: JSON.stringify(this.state.filters),
    });
    window.open(`/api/method/${PPWO_API}.export_excel?${params.toString()}`, "_blank");
}

export_selected_csv() {
    if (this.state.selected.size === 0) {
        frappe.msgprint(__("Please select at least one row to export."));
        return;
    }
    const params = new URLSearchParams({
        cmd: `${PPWO_API}.export_excel`,
        sales_orders: JSON.stringify(Array.from(this.state.selected)),
    });
    window.open(`/api/method/${PPWO_API}.export_excel?${params.toString()}`, "_blank");
    frappe.show_alert({ message: __("Exporting {0} selected rows…", [this.state.selected.size]), indicator: "green" });
}

// ADD this new helper — joins names one per line inside a single cell

_format_doc_list(names) {
    if (!names || !names.length) return "";
    return names.join("|");
}

// ADD this new helper — normalises '—' / '-' / 'N/A' placeholders to blank
_clean(value) {
    if (value === null || value === undefined) return "";
    const str = String(value).trim();
    if (["—", "-", "--", "N/A", "n/a", "None"].includes(str)) return "";
    return str;
}

// REPLACE the existing _csv_value function (needs to preserve \r\n inside quotes):
_csv_value(val) {
    if (val === null || val === undefined) return '""';
    const str = String(val).replace(/"/g, '""');
    return `"${str}"`;
}

	bulk_assign_dialog() {
		if (!this.state.selected.size) {
			frappe.msgprint(__("Select one or more rows first."));
			return;
		}
		const d = new frappe.ui.Dialog({
			title: __("Assign Selected Sales Orders"),
			fields: [
				{ fieldtype: "Link", fieldname: "assign_to", label: "Assign To", options: "User", reqd: 1 },
				{ fieldtype: "Small Text", fieldname: "description", label: "Note" },
			],
			primary_action_label: __("Assign"),
			primary_action: (values) => {
				frappe
					.call({
						method: `${PPWO_API}.bulk_assign`,
						args: {
							sales_orders: JSON.stringify(Array.from(this.state.selected)),
							assign_to: values.assign_to,
							description: values.description,
						},
					})
					.then((r) => {
						frappe.show_alert({ message: __("Assigned {0} sales orders", [r.message.created]), indicator: "green" });
						d.hide();
					});
			},
		});
		d.show();
	}

	// ------------------------------------------------------------------ //
	// Grid
	// ------------------------------------------------------------------ //
	build_grid_head() {
		const cols = [
			"", "Sales Order", "Customer", "OMR", "OMR Status", "BMR", "BMR Status", "Production Plan",
			"PP Update Req.", "PP Updated", "Work Order", "WO Update Req.", "WO Updated",
			"Stage", "Pending At", "Severity", "Updated By", "Updated Time", "Remarks",
		];
		
		this.$body.find("table.ppwo-grid thead").html(`<tr>
    <th><input type="checkbox" class="ppwo-select-all" title="Select/Deselect All"></th>
    ${cols.slice(1).map((c) => `<th>${c}</th>`).join("")}
</tr>`);
	}

	bind_grid_events() {
		this.$body.on("click", "#ppwo-load-more", () => {
			this.state.start += this.state.page_length;
			this.fetch_grid(true);
		});
		this.$body.on("click", "tbody tr[data-so]", (e) => {
			if ($(e.target).is("input.ppwo-row-check")) return;
			this.open_drawer($(e.currentTarget).data("so"));
		});
		// REPLACE the existing ppwo-row-check handler:
this.$body.on("click", ".ppwo-row-check", (e) => {
    e.stopPropagation();
    const so = $(e.currentTarget).closest("tr").data("so");
    if (e.currentTarget.checked) this.state.selected.add(so);
    else this.state.selected.delete(so);
    this._update_export_buttons();
});
		this.$body.on("click", ".ppwo-row-action", (e) => {
			e.stopPropagation();
			const $t = $(e.currentTarget);
			const doctype = $t.data("doctype");
			const name = $t.data("name");
			if (doctype && name) frappe.set_route("Form", doctype, name);
		});
		this.$body.on("click", ".ppwo-list-view-btn", (e) => {
			e.stopPropagation();
			const $t = $(e.currentTarget);
			const doctype = $t.data("doctype");
			let filters = {};
			try {
				filters = JSON.parse($t.attr("data-filters"));
			} catch (err) {
				filters = {};
			}
			frappe.route_options = filters;
			frappe.set_route("List", doctype, "list");
		});
		// ADD these event handlers in bind_grid_events:
this.$body.on("click", ".ppwo-select-all", (e) => {
    e.stopPropagation();
    const checked = e.currentTarget.checked;
    const $checkboxes = this.$body.find("tbody tr .ppwo-row-check");
    $checkboxes.prop("checked", checked);
    
    if (checked) {
        this.$body.find("tbody tr[data-so]").each((i, tr) => {
            this.state.selected.add($(tr).data("so"));
        });
    } else {
        this.$body.find("tbody tr[data-so]").each((i, tr) => {
            this.state.selected.delete($(tr).data("so"));
        });
    }
    this._update_export_buttons();
});
	}
	// ADD this new function:
_update_export_buttons() {
    const selected_count = this.state.selected.size;
    const $export_all = this.$body.find('.ppwo-btn[data-act="export"]');
    const $export_selected = this.$body.find('.ppwo-btn[data-act="export_selected"]');
    
    if (selected_count > 0) {
        $export_all.hide();
        $export_selected.show().text(`⇩ Export Selected (${selected_count})`);
    } else {
        $export_all.show();
        $export_selected.hide();
    }
    
    // Update select all checkbox state
    const total_visible = this.$body.find("tbody tr[data-so]").length;
    const checked_visible = this.$body.find("tbody tr .ppwo-row-check:checked").length;
    const $select_all = this.$body.find(".ppwo-select-all");
    
    if (total_visible > 0 && checked_visible === total_visible) {
        $select_all.prop("checked", true).prop("indeterminate", false);
    } else if (checked_visible > 0) {
        $select_all.prop("checked", false).prop("indeterminate", true);
    } else {
        $select_all.prop("checked", false).prop("indeterminate", false);
    }
}

	render_skeleton_rows(n = 8) {
		const cols = 19;
		let rows = "";
		for (let i = 0; i < n; i++) {
			rows += `<tr>${Array(cols)
				.fill('<td><div class="ppwo-skel" style="height:14px;width:80%;"></div></td>')
				.join("")}</tr>`;
		}
		this.$body.find("table.ppwo-grid tbody").html(rows);
	}

	badge(b) {
		if (!b) return "";
		return `<span class="ppwo-badge ${b.key}">${b.emoji} ${b.label}</span>`;
	}

	stage_rail(stages) {
		return `<div class="ppwo-rail">${stages
			.map((s) => {
				const has_pulse = s.state === "pending" || s.state === "blocked";
				return `<div class="seg ${s.state}" title="${s.label}: ${s.state}">${has_pulse ? '<div class="pulse"></div>' : ""}</div>`;
			})
			.join("")}</div>`;
	}

	doc_ref_cell(doctype, docs, list_filters) {
		if (!docs || !docs.length) return '<span class="ppwo-dash">—</span>';
		if (docs.length === 1) {
			return `<span class="ppwo-cell-link ppwo-row-action" data-doctype="${doctype}" data-name="${docs[0].name}">${docs[0].name}</span>`;
		}
		const label = `${docs.length} ${doctype}${docs.length > 1 ? "s" : ""}`;
		return `<button class="ppwo-chip-btn ppwo-list-view-btn" data-doctype="${doctype}" data-filters='${frappe.utils.escape_html(
			JSON.stringify(list_filters)
		)}'>${label}<span class="arrow">↗</span></button>`;
	}

	render_row(r) {
		const so_link = `<span class="ppwo-mono ppwo-cell-link ppwo-row-action" data-doctype="Sales Order" data-name="${r.sales_order}">${r.sales_order}</span>`;
		const omr_cell = this.doc_ref_cell("Order Modification Request", r.omr ? [r.omr] : [], { sales_order: r.sales_order });
		const bmr_cell = this.doc_ref_cell("Bom Modification Request", r.bmr_list, { name: ["in", (r.bmr_list || []).map((b) => b.name)] });
		const pp_cell = this.doc_ref_cell("Production Plan", r.pp ? [r.pp] : [], { name: ["in", r.pp ? [r.pp.name] : []] });
		// FIX: WO list-view now filters by production_plan (PP→WO flow), not by sales_order
		const wo_cell = this.doc_ref_cell("Work Order", r.wo_list, r.pp ? { production_plan: r.pp.name } : { sales_order: r.sales_order });
		const row_class_map = { Critical: "ppwo-row-critical", High: "ppwo-row-high", Medium: "ppwo-row-medium", Waiting: "ppwo-row-waiting" };
		const row_class = row_class_map[r.severity] || "";
	
		return `<tr data-so="${r.sales_order}" class="${row_class}">
			<td><input type="checkbox" class="ppwo-row-check"></td>
			<td>${so_link}</td>
			<td title="${frappe.utils.escape_html(r.customer_name || "")}">${frappe.utils.escape_html(r.customer_name || "")}</td>
			<td>${omr_cell}</td>
			<td>${this.badge(r.omr_badge)}</td>
			<td>${bmr_cell}</td>
			<td>${this.badge(r.bmr_badge)}</td>
			<td>${pp_cell}</td>
			<td>${this.badge(r.pp_required_badge)}</td>
			<td>${this.badge(r.pp_updated_badge)}</td>
			<td>${wo_cell}</td>
			<td>${this.badge(r.wo_required_badge)}</td>
			<td>${this.badge(r.wo_updated_badge)}</td>
			<td class="ppwo-nowrap-safe">${this.stage_rail(r.stages)}</td>
			<td>${r.pending_at}</td>
			<td><span class="ppwo-sev ${r.severity}">${r.severity}</span></td>
			<td title="${frappe.utils.escape_html(r.modified_by || "")}">${frappe.utils.escape_html(r.modified_by || "")}</td>
			<td class="ppwo-mono" style="font-size:11px;">${frappe.datetime.prettyDate(r.modified)}</td>
			<td title="${r.is_pending ? "Awaiting action at " + r.current_stage : ""}">${r.is_pending ? "Awaiting action at " + r.current_stage : '<span class="ppwo-dash">—</span>'}</td>
		</tr>`;
	}

	fetch_dashboard() {
		return frappe
			.call({ method: `${PPWO_API}.get_dashboard_data`, args: { filters: JSON.stringify(this.state.filters) } })
			.then((r) => this.render_kpis(r.message))
			.catch((e) => console.error("PPWO get_dashboard_data failed:", e));
	}

	fetch_grid(append) {
    this.state.loading = true;
    if (!append) this.render_skeleton_rows();
    return frappe
        .call({
            method: `${PPWO_API}.get_grid_data`,
            args: { filters: JSON.stringify(this.state.filters), start: this.state.start, page_length: this.state.page_length },
        })
        .then((r) => {
            const data = r.message || { rows: [], total: 0 };
            this.state.total = data.total;
            this.state.rows = append ? this.state.rows.concat(data.rows) : data.rows;
            const $tbody = this.$body.find("table.ppwo-grid tbody");
            if (append) $tbody.append(data.rows.map((row) => this.render_row(row)).join(""));
            else $tbody.html(this.state.rows.map((row) => this.render_row(row)).join("") || `<tr><td colspan="19" style="text-align:center;padding:30px;color:var(--ppwo-text-dim);">No rows match these filters. </td></tr>`);
            this.$body.find("#ppwo-load-more").toggle(this.state.rows.length < this.state.total);
            
            // ============ ADD HERE - AFTER the above line ============
            // Reset select all checkbox
            this.$body.find(".ppwo-select-all").prop("checked", false).prop("indeterminate", false);
            
            // Restore checked state for previously selected rows
            this.state.selected.forEach(so => {
                this.$body.find(`tr[data-so="${so}"] .ppwo-row-check`).prop("checked", true);
            });
            
            // Update button states
            this._update_export_buttons();
            // =========================================================
            
            this.state.loading = false;
        })
        .catch((e) => {
            this.state.loading = false;
            console.error("PPWO get_grid_data failed:", e);
        });
}

	fetch_charts() {
		return frappe
			.call({ method: `${PPWO_API}.get_charts_data`, args: { filters: JSON.stringify(this.state.filters) } })
			.then((r) => this.render_charts(r.message || {}))
			.catch((e) => console.error("PPWO get_charts_data failed:", e));
	}

	refresh_all(user_triggered) {
		if (user_triggered) frappe.show_alert({ message: __("Refreshing…"), indicator: "blue" });
		this.state.start = 0;
		this.state.selected.clear(); // ADD THIS LINE
		return Promise.all([this.fetch_dashboard(), this.fetch_grid(false), this.fetch_charts()]);
	}

	// ------------------------------------------------------------------ //
	// Charts
	// ------------------------------------------------------------------ //
	render_charts(d) {
		this.render_chart_compact(".c-branch", { type: "bar" }, d.branch && {
			labels: d.branch.labels,
			datasets: [{ name: "Pending", values: d.branch.pending }, { name: "Total", values: d.branch.total }],
		}, ["#E86161", "#2490EF"]);

		this.render_chart_compact(".c-status", { type: "donut" }, d.status_distribution && {
			labels: d.status_distribution.labels,
			datasets: [{ values: d.status_distribution.values }],
		}, ["#E86161", "#F5A623", "#4C9CE2", "#98A6BF", "#5EBB63"]);

		if (d.funnel) {
			const labels = Object.keys(d.funnel);
			const values = Object.values(d.funnel);
			this.render_chart_compact(".c-funnel", { type: "bar" }, { labels, datasets: [{ name: "Count", values }] }, ["#7CB9F0"]);
		}

		this.render_chart_compact(".c-trend", { type: "line" }, d.trend && {
			labels: d.trend.labels,
			datasets: [{ name: "Pending opened", values: d.trend.values }],
		}, ["#2490EF"]);

		// Render Branch Performance
		const $perf = this.$body.find(".c-branch-perf").empty();
		(d.branch_performance || []).forEach((b) => {
			$perf.append(`
				<div class="ppwo-branch-perf-item">
					<div class="branch-name" title="${frappe.utils.escape_html(b.branch)}">${frappe.utils.escape_html(b.branch)}</div>
					<div class="branch-bar">
						<div class="branch-bar-inner" style="width:${b.sync_pct}%;"></div>
					</div>
					<div class="branch-pct">${b.sync_pct}%</div>
					<div class="branch-count">${b.synced}/${b.total}</div>
				</div>`);
		});
	}

	render_chart_compact(sel, opts, data, colors) {
		const el = this.$body.find(sel)[0];
		if (!el || !data) return;
		el.innerHTML = "";
		if (!window.frappe || !frappe.Chart) return;
		
		const width = this.$body.width();
		const height = width < 480 ? 150 : width < 768 ? 170 : 200;
		
		try {
			new frappe.Chart(el, { 
				data, 
				type: opts.type, 
				height: height, 
				colors: colors, 
				axisOptions: { xAxisMode: "tick" },
				chartOptions: { 
					responsive: true,
					maintainAspectRatio: false 
				}
			});
		} catch (e) {
			// Chart library not available
		}
	}

	// ------------------------------------------------------------------ //
	// Drawer
	// ------------------------------------------------------------------ //
	bind_drawer_events() {
		this.$body.find(".ppwo-drawer-overlay, .ppwo-drawer .close-btn").on("click", () => this.close_drawer());
		$(document).on("keydown.ppwo", (e) => {
			if (e.key === "Escape") this.close_drawer();
		});
	}

	open_drawer(sales_order) {
    this.$body.find(".ppwo-drawer-overlay").addClass("open");
    this.$body.find(".ppwo-drawer").addClass("open");
    this.$body.find(".ppwo-drawer-content").html(`<div class="ppwo-skel" style="height:20px;width:60%;margin-bottom:14px;"></div>
        <div class="ppwo-skel" style="height:100px;width:100%;"></div>`);
    
    // FIX: Use collect_filters() instead of this.state.filters to get current filter state
    const filters = this.collect_filters();
    
    frappe.call({ 
        method: `${PPWO_API}.get_row_detail`, 
        args: { 
            sales_order, 
            filters: JSON.stringify(filters) 
        } 
    }).then((r) => this.render_drawer(r.message));
}
	close_drawer() {
		this.$body.find(".ppwo-drawer-overlay").removeClass("open");
		this.$body.find(".ppwo-drawer").removeClass("open");
	}

	create_accordion_section(title, docs, doctype, filters = {}) {
		if (!docs || !docs.length) return "";
		
		const max_visible = 3;
		const visible_docs = docs.slice(0, max_visible);
		const hidden_count = docs.length - max_visible;
		
		return `
			<div class="ppwo-accordion">
				<div class="ppwo-accordion-toggle">
					<span>${title} (${docs.length})</span>
					<span class="ppwo-accordion-arrow">▼</span>
				</div>
				<div class="ppwo-accordion-content">
					${visible_docs.map(doc => `
						<div class="ppwo-doc-row">
							<span class="ppwo-cell-link ppwo-doc-link" data-doctype="${doctype}" data-name="${doc.name}" style="cursor:pointer;">${doc.name}</span>
							<span style="color:var(--ppwo-text-dim); font-size:10px;">${doc.status || doc.workflow_state || ""}</span>
						</div>
					`).join("")}
					${hidden_count > 0 ? `
						<div style="margin-top:8px; text-align:center;">
							<button class="ppwo-btn ppwo-view-all-btn" style="width:100%; font-size:11px; padding:4px 8px;"
								data-doctype="${doctype}" data-filters='${frappe.utils.escape_html(JSON.stringify(filters))}'>
								View All ${hidden_count} More ↗
							</button>
						</div>
					` : ""}
				</div>
			</div>
		`;
	}

	render_drawer(d) {
    if (!d) return;
    const { so, row, pending_actions, history } = d;
    const $c = this.$body.find(".ppwo-drawer-content");
    
    // Safety checks for all data
    const pp_docs = (row && row.pp) ? [row.pp] : [];
    const wo_docs = (row && row.wo_list) || [];
    const stages = (row && row.stages) || [];
    const severity = (row && row.severity) || "Low";
    const omr_badge = (row && row.omr_badge) || { key: "not_required", emoji: "", label: "Not Required" };
    const omr = (row && row.omr) || null;
    
    $c.html(`
        <h3>${so.name || ""}</h3>
        <div style="color:var(--ppwo-text-dim);font-size:13px;margin-bottom:8px;">${frappe.utils.escape_html(so.customer_name || "")} · ${so.branch || "—"}</div>
        <span class="ppwo-sev ${severity}">${severity}</span> ${this.badge(omr_badge)}

        <div class="section-title">Stage Rail</div>
        ${this.stage_rail(stages)}

        <div class="section-title">Pending Actions</div>
        ${(pending_actions || []).map((a) => `<div class="ppwo-pending-action">⚠️ ${frappe.utils.escape_html(a)}</div>`).join("")}

        <div class="section-title">Linked Documents</div>
        ${omr ? this.create_accordion_section("Order Modification Request", [omr], "Order Modification Request", { sales_order: so.name }) : ""}
        ${(row && row.bmr_list && row.bmr_list.length) ? this.create_accordion_section("BOM Modification Requests", row.bmr_list, "Bom Modification Request", { sales_order: so.name }) : ""}
        ${pp_docs.length ? this.create_accordion_section("Production Plans", pp_docs, "Production Plan", { sales_order: so.name }) : ""}
        ${wo_docs.length ? this.create_accordion_section("Work Orders", wo_docs, "Work Order", (row && row.pp) ? { production_plan: row.pp.name } : { sales_order: so.name }) : ""}

        <div class="section-title">History</div>
        <div class="ppwo-history-section" style="max-height:300px; overflow-y:auto;">
            ${(history || []).length ? history
                .map(
                    (h) => `<div class="ppwo-timeline-item"><div class="dot"></div>
                    <div><b>${h.doctype || ""}</b> ${h.name || ""} — ${h.event || ""}${h.state ? " (" + h.state + ")" : ""}<br>
                    <span style="color:var(--ppwo-text-dim);">${h.time ? frappe.datetime.prettyDate(h.time) : ""} · ${h.user || ""}</span></div></div>`
                )
                .join("") : '<div style="color:var(--ppwo-text-dim); padding:10px;">No history available</div>'}
        </div>

        <div style="margin-top:20px;display:flex;gap:8px;flex-wrap:wrap;">
            <button class="ppwo-btn ppwo-drawer-refresh">↻ Refresh Status</button>
            <button class="ppwo-btn primary ppwo-drawer-open-so">Open Sales Order</button>
        </div>
    `);
    
    // Rest of the drawer bindings remain the same...
    $c.find(".ppwo-accordion-toggle").on("click", function() {
        $(this).toggleClass("active");
        $(this).next(".ppwo-accordion-content").slideToggle(200);
    });
    
    $c.find(".ppwo-drawer-refresh").on("click", (e) => {
        this.ripple(e.currentTarget, e);
        const filters = this.collect_filters();
        frappe.call({ 
            method: `${PPWO_API}.refresh_row`, 
            args: { 
                sales_order: so.name, 
                filters: JSON.stringify(filters) 
            } 
        }).then(() => this.open_drawer(so.name));
    });
    
    $c.find(".ppwo-drawer-open-so").on("click", () => frappe.set_route("Form", "Sales Order", so.name));
    
    $c.find(".ppwo-doc-link").on("click", (e) => {
        e.stopPropagation();
        const doctype = $(e.currentTarget).data("doctype");
        const name = $(e.currentTarget).data("name");
        if (doctype && name) frappe.set_route("Form", doctype, name);
    });
    
    $c.find(".ppwo-view-all-btn").on("click", (e) => {
        e.stopPropagation();
        const $btn = $(e.currentTarget);
        const doctype = $btn.data("doctype");
        let filters = {};
        try {
            filters = JSON.parse($btn.attr("data-filters"));
        } catch (err) {
            filters = {};
        }
        frappe.route_options = filters;
        frappe.set_route("List", doctype, "list");
    });
}

	// ------------------------------------------------------------------ //
	// Celebration
	// ------------------------------------------------------------------ //
	celebrate() {
		frappe.show_alert({ message: __("🎉 Everything is fully synchronized!"), indicator: "green" });
		const canvas = document.createElement("canvas");
		canvas.id = "ppwo-confetti-canvas";
		canvas.width = window.innerWidth;
		canvas.height = window.innerHeight;
		document.body.appendChild(canvas);
		const ctx = canvas.getContext("2d");
		const colors = ["#2490EF", "#7CB9F0", "#5EBB63", "#F5A623", "#E86161"];
		const particles = Array.from({ length: 140 }, () => ({
			x: Math.random() * canvas.width,
			y: -20 - Math.random() * canvas.height * 0.3,
			r: 3 + Math.random() * 4,
			c: colors[Math.floor(Math.random() * colors.length)],
			vy: 2 + Math.random() * 3,
			vx: -1.5 + Math.random() * 3,
			rot: Math.random() * 360,
		}));
		let frame = 0;
		const tick = () => {
				ctx.clearRect(0, 0, canvas.width, canvas.height);
				particles.forEach((p) => {
				p.x += p.vx;
				p.y += p.vy;
				p.rot += 4;
				ctx.save();
				ctx.translate(p.x, p.y);
				ctx.rotate((p.rot * Math.PI) / 180);
				ctx.fillStyle = p.c;
				ctx.fillRect(-p.r / 2, -p.r / 2, p.r, p.r * 1.6);
				ctx.restore();
			});
			frame++;
			if (frame < 130) requestAnimationFrame(tick);
			else canvas.remove();
		};
		tick();
	}
}