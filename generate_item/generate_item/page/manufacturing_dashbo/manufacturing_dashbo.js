// frappe.pages['manufacturing-dashbo'].on_page_load = function(wrapper) {
// 	var page = frappe.ui.make_app_page({
// 		parent: wrapper,
// 		title: 'Manufacturing Dashboard',
// 		single_column: true
// 	});
// }
frappe.pages['manufacturing-dashbo'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Manufacturing Dashboard',
		single_column: true
	});

	// =========================================================
	// CSS
	// =========================================================
	var page_css = `
	<style id="mfg-dash-css">
	.mfg-dash-wrap *{margin:0;padding:0;box-sizing:border-box}
	.mfg-dash-wrap{--bg-primary:#f6f8fc;--bg-card:#ffffff;--bg-glass:rgba(255,255,255,0.65);--bg-tab:#f1f4fa;--bg-tab-active:#ffffff;--text-primary:#0b1a30;--text-secondary:#4a5d73;--text-muted:#8a9bb0;--border-color:#e9edf4;--shadow-sm:0 2px 8px rgba(0,0,0,0.04);--shadow-md:0 8px 32px rgba(0,0,0,0.06),0 2px 8px rgba(0,0,0,0.03);--shadow-lg:0 20px 60px rgba(0,0,0,0.08),0 8px 24px rgba(0,0,0,0.04);--radius-sm:10px;--radius-md:16px;--radius-lg:24px;--radius-full:9999px;--transition:all 0.3s cubic-bezier(0.4,0,0.2,1);--gradient-header:linear-gradient(135deg,#0b1a30 0%,#1a365d 50%,#2a4a7a 100%);--glass-border:rgba(255,255,255,0.2);--kpi-gradient-1:linear-gradient(135deg,#1a365d,#2a4a7a);--kpi-gradient-2:linear-gradient(135deg,#0d9488,#14b8a6);--kpi-gradient-3:linear-gradient(135deg,#7c3aed,#8b5cf6);--kpi-gradient-4:linear-gradient(135deg,#dc2626,#ef4444);--badge-success:#dff0e6;--badge-success-text:#1a6e3b;--badge-warning:#fef3dd;--badge-warning-text:#9e6f1a;--badge-danger:#fae7e7;--badge-danger-text:#b13a3a;--badge-info:#e2ebf9;--badge-info-text:#1a4b7a;--badge-neutral:#e9edf4;--badge-neutral-text:#4a5d73;--chart-bar-1:#2a4a7a;--chart-bar-2:#4a7aaa;--chart-bar-3:#7aaadd;--chart-bar-4:#b5d4f0}
	[data-theme="dark"] .mfg-dash-wrap{--bg-primary:#0d1117;--bg-card:#161b22;--bg-glass:rgba(22,27,34,0.8);--bg-tab:#21262d;--bg-tab-active:#30363d;--text-primary:#f0f6fc;--text-secondary:#8b949e;--text-muted:#6e7681;--border-color:#30363d;--shadow-sm:0 2px 8px rgba(0,0,0,0.3);--shadow-md:0 8px 32px rgba(0,0,0,0.4);--shadow-lg:0 20px 60px rgba(0,0,0,0.5);--gradient-header:linear-gradient(135deg,#0d1117 0%,#161b22 50%,#21262d 100%);--glass-border:rgba(255,255,255,0.06);--badge-success:#1e3a2f;--badge-success-text:#7ee8a0;--badge-warning:#3d2e1a;--badge-warning-text:#f5c542;--badge-danger:#3d1a1a;--badge-danger-text:#f87171;--badge-info:#1a2a3d;--badge-info-text:#6a9fd8;--badge-neutral:#21262d;--badge-neutral-text:#8b949e;--chart-bar-1:#58a6ff;--chart-bar-2:#79c0ff;--chart-bar-3:#a5d6ff;--chart-bar-4:#d2e8ff;--kpi-gradient-1:linear-gradient(135deg,#1a365d,#2a4a7a);--kpi-gradient-2:linear-gradient(135deg,#0d9488,#14b8a6);--kpi-gradient-3:linear-gradient(135deg,#7c3aed,#8b5cf6);--kpi-gradient-4:linear-gradient(135deg,#dc2626,#ef4444)}
	.mfg-dash-wrap{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:var(--bg-primary);color:var(--text-primary);min-height:100vh;padding:20px;transition:var(--transition);line-height:1.5}
	.mfg-dash-wrap ::-webkit-scrollbar{width:6px;height:6px}
	.mfg-dash-wrap ::-webkit-scrollbar-track{background:transparent}
	.mfg-dash-wrap ::-webkit-scrollbar-thumb{background:var(--text-muted);border-radius:10px}
	.mfg-dash-wrap ::-webkit-scrollbar-thumb:hover{background:var(--text-secondary)}
	.mfg-dash-wrap .dashboard{max-width:1480px;margin:0 auto;display:flex;flex-direction:column;gap:24px}
	.mfg-dash-wrap .header-glass{background:var(--gradient-header);border-radius:var(--radius-lg);padding:20px 28px;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:16px;position:relative;z-index:10;box-shadow:var(--shadow-lg);border:1px solid var(--glass-border);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}
	.mfg-dash-wrap .header-effects{position:absolute;top:0;left:0;right:0;bottom:0;overflow:hidden;border-radius:var(--radius-lg);pointer-events:none;z-index:0}
	.mfg-dash-wrap .header-effects::before{content:'';position:absolute;top:-50%;right:-20%;width:400px;height:400px;background:radial-gradient(circle,rgba(255,255,255,0.06) 0%,transparent 70%);border-radius:50%;pointer-events:none}
	.mfg-dash-wrap .header-effects::after{content:'';position:absolute;bottom:-40%;left:-10%;width:300px;height:300px;background:radial-gradient(circle,rgba(255,255,255,0.04) 0%,transparent 70%);border-radius:50%;pointer-events:none}
	.mfg-dash-wrap .header-left{display:flex;align-items:center;gap:14px;position:relative;z-index:1}
	.mfg-dash-wrap .header-left .logo-icon{width:44px;height:44px;background:rgba(255,255,255,0.12);border-radius:var(--radius-sm);display:flex;align-items:center;justify-content:center;color:#fff;font-size:22px;backdrop-filter:blur(8px);border:1px solid rgba(255,255,255,0.15);flex-shrink:0}
	.mfg-dash-wrap .header-left h1{font-size:22px;font-weight:700;color:#fff;letter-spacing:-0.3px}
	.mfg-dash-wrap .header-left h1 span{font-weight:400;font-size:16px;opacity:0.7;margin-left:6px}
	.mfg-dash-wrap .header-center{display:flex;align-items:center;gap:12px;flex-wrap:wrap;position:relative;z-index:1;flex:1 1 auto;justify-content:center}
	.mfg-dash-wrap .header-center .filter-chip{background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.12);padding:6px 16px;border-radius:var(--radius-full);font-size:13px;font-weight:500;color:rgba(255,255,255,0.8);display:flex;align-items:center;gap:8px;cursor:pointer;transition:var(--transition);backdrop-filter:blur(4px);user-select:none}
	.mfg-dash-wrap .header-center .filter-chip:hover,.mfg-dash-wrap .header-center .filter-chip.active{background:rgba(255,255,255,0.18);color:#fff}
	.mfg-dash-wrap .header-center .filter-chip i{font-size:11px;opacity:0.7}
	.mfg-dash-wrap .header-right{display:flex;align-items:center;gap:12px;position:relative;z-index:1}
	.mfg-dash-wrap .header-right .icon-btn{width:40px;height:40px;border-radius:50%;background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.1);color:rgba(255,255,255,0.8);display:flex;align-items:center;justify-content:center;cursor:pointer;transition:var(--transition);font-size:16px;backdrop-filter:blur(4px);position:relative}
	.mfg-dash-wrap .header-right .icon-btn:hover{background:rgba(255,255,255,0.18);color:#fff;transform:scale(1.05)}
	.mfg-dash-wrap .header-right .icon-btn .badge-dot{position:absolute;top:6px;right:6px;width:8px;height:8px;border-radius:50%;background:#ef4444;border:2px solid #1a365d}
	.mfg-dash-wrap .theme-toggle{background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.1);border-radius:var(--radius-full);padding:6px 10px;display:flex;align-items:center;gap:6px;cursor:pointer;transition:var(--transition);color:rgba(255,255,255,0.7);font-size:14px}
	.mfg-dash-wrap .theme-toggle:hover{background:rgba(255,255,255,0.15);color:#fff}
	.mfg-dash-wrap .theme-toggle i{font-size:14px}
	.mfg-dash-wrap .theme-toggle .fa-moon{display:inline-block}
	[data-theme="dark"] .mfg-dash-wrap .theme-toggle .fa-moon{display:none}
	.mfg-dash-wrap .theme-toggle .fa-sun{display:none}
	[data-theme="dark"] .mfg-dash-wrap .theme-toggle .fa-sun{display:inline-block}
	.mfg-dash-wrap .kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px}
	.mfg-dash-wrap .kpi-card{background:var(--bg-card);border-radius:var(--radius-md);padding:20px 24px;box-shadow:var(--shadow-sm);border:1px solid var(--border-color);transition:var(--transition);position:relative;overflow:hidden}
	.mfg-dash-wrap .kpi-card:hover{transform:translateY(-3px);box-shadow:var(--shadow-md);border-color:transparent}
	.mfg-dash-wrap .kpi-card .kpi-top{display:flex;align-items:flex-start;justify-content:space-between}
	.mfg-dash-wrap .kpi-card .kpi-icon{width:44px;height:44px;border-radius:var(--radius-sm);display:flex;align-items:center;justify-content:center;font-size:20px;color:#fff;flex-shrink:0}
	.mfg-dash-wrap .kpi-card .kpi-icon.blue{background:var(--kpi-gradient-1)}
	.mfg-dash-wrap .kpi-card .kpi-icon.teal{background:var(--kpi-gradient-2)}
	.mfg-dash-wrap .kpi-card .kpi-icon.purple{background:var(--kpi-gradient-3)}
	.mfg-dash-wrap .kpi-card .kpi-icon.red{background:var(--kpi-gradient-4)}
	.mfg-dash-wrap .kpi-card .kpi-label{font-size:13px;font-weight:500;color:var(--text-secondary);margin-top:12px}
	.mfg-dash-wrap .kpi-card .kpi-value{font-size:28px;font-weight:800;color:var(--text-primary);letter-spacing:-0.5px;line-height:1.2}
	.mfg-dash-wrap .kpi-card .kpi-trend{display:inline-flex;align-items:center;gap:4px;font-size:13px;font-weight:600;padding:2px 10px;border-radius:var(--radius-full);margin-top:4px}
	.mfg-dash-wrap .kpi-card .kpi-trend.up{color:#1a6e3b;background:var(--badge-success)}
	.mfg-dash-wrap .kpi-card .kpi-trend.down{color:#b13a3a;background:var(--badge-danger)}
	.mfg-dash-wrap .kpi-card .kpi-trend.neutral{color:var(--text-muted);background:var(--badge-neutral)}
	.mfg-dash-wrap .kpi-card .kpi-trend i{font-size:11px}
	.mfg-dash-wrap .main-layout{display:block;}
	.mfg-dash-wrap .content-area{display:flex;flex-direction:column;gap:20px;min-width:0}
	.mfg-dash-wrap .tabs-pill{display:flex;gap:4px;background:var(--bg-tab);border-radius:var(--radius-md);padding:4px;border:1px solid var(--border-color);flex-wrap:wrap;box-shadow:var(--shadow-sm)}
	.mfg-dash-wrap .tab-btn{flex:1 1 auto;min-width:120px;padding:10px 20px;border:none;background:transparent;border-radius:var(--radius-sm);font-size:14px;font-weight:500;color:var(--text-secondary);cursor:pointer;transition:var(--transition);display:flex;align-items:center;justify-content:center;gap:8px;white-space:nowrap;font-family:'Inter',sans-serif}
	.mfg-dash-wrap .tab-btn i{font-size:15px;opacity:0.7;transition:var(--transition)}
	.mfg-dash-wrap .tab-btn:hover{color:var(--text-primary);background:rgba(255,255,255,0.4)}
	.mfg-dash-wrap .tab-btn.active{background:var(--bg-tab-active);color:var(--text-primary);box-shadow:var(--shadow-sm)}
	.mfg-dash-wrap .tab-btn.active i{opacity:1}
	.mfg-dash-wrap .tab-btn .tab-badge{background:var(--badge-neutral);color:var(--text-secondary);font-size:11px;font-weight:600;padding:0 10px;border-radius:var(--radius-full);line-height:20px;transition:var(--transition)}
	.mfg-dash-wrap .tab-btn.active .tab-badge{background:var(--text-primary);color:var(--bg-tab-active)}
	.mfg-dash-wrap .tab-panel{display:none;animation:fadeSlide 0.35s ease forwards}
	.mfg-dash-wrap .tab-panel.active{display:block}
	@keyframes fadeSlide{0%{opacity:0;transform:translateY(12px)}100%{opacity:1;transform:translateY(0)}}
	.mfg-dash-wrap .table-card{background:var(--bg-card);border-radius:var(--radius-md);border:1px solid var(--border-color);box-shadow:var(--shadow-sm);overflow:hidden;transition:var(--transition)}
	.mfg-dash-wrap .table-card:hover{box-shadow:var(--shadow-md)}
	.mfg-dash-wrap .table-card .table-header{padding:16px 20px;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px;border-bottom:1px solid var(--border-color)}
	.mfg-dash-wrap .table-card .table-header .title{font-size:15px;font-weight:600;color:var(--text-primary);display:flex;align-items:center;gap:8px}
	.mfg-dash-wrap .table-card .table-header .title i{color:var(--text-muted);font-size:16px}
	.mfg-dash-wrap .table-card .table-header .actions{display:flex;gap:8px;align-items:center}
	.mfg-dash-wrap .table-card .table-header .actions button{padding:6px 14px;border:1px solid var(--border-color);background:transparent;border-radius:var(--radius-full);font-size:12px;font-weight:500;color:var(--text-secondary);cursor:pointer;transition:var(--transition);display:flex;align-items:center;gap:6px;font-family:'Inter',sans-serif}
	.mfg-dash-wrap .table-card .table-header .actions button:hover{background:var(--bg-tab);border-color:var(--text-muted)}
	.mfg-dash-wrap .table-card .table-header .actions .btn-primary{background:var(--text-primary);color:var(--bg-card);border-color:var(--text-primary)}
	.mfg-dash-wrap .table-card .table-header .actions .btn-primary:hover{opacity:0.85;transform:scale(0.98)}
	.mfg-dash-wrap .table-scroll{overflow-x:auto;padding:0 4px 4px 4px}
	.mfg-dash-wrap table{width:100%;border-collapse:collapse;font-size:14px;min-width:600px}
	.mfg-dash-wrap table thead th{text-align:left;padding:12px 18px;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.4px;color:var(--text-muted);border-bottom:1px solid var(--border-color);background:var(--bg-primary)}
	.mfg-dash-wrap table tbody td{padding:12px 18px;border-bottom:1px solid var(--border-color);color:var(--text-primary);font-weight:450;transition:var(--transition)}
	.mfg-dash-wrap table tbody tr:last-child td{border-bottom:none}
	.mfg-dash-wrap table tbody tr{transition:var(--transition);cursor:pointer}
	.mfg-dash-wrap table tbody tr:hover{background:var(--bg-tab)}
	.mfg-dash-wrap .status-pill{display:inline-flex;align-items:center;gap:6px;padding:3px 14px;border-radius:var(--radius-full);font-size:12px;font-weight:600;white-space:nowrap}
	.mfg-dash-wrap .status-pill.success{background:var(--badge-success);color:var(--badge-success-text)}
	.mfg-dash-wrap .status-pill.warning{background:var(--badge-warning);color:var(--badge-warning-text)}
	.mfg-dash-wrap .status-pill.danger{background:var(--badge-danger);color:var(--badge-danger-text)}
	.mfg-dash-wrap .status-pill.info{background:var(--badge-info);color:var(--badge-info-text)}
	.mfg-dash-wrap .status-pill.neutral{background:var(--badge-neutral);color:var(--badge-neutral-text)}
	.mfg-dash-wrap .status-pill i{font-size:8px}
	.mfg-dash-wrap .priority-pill{padding:2px 12px;border-radius:var(--radius-full);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.3px}
	.mfg-dash-wrap .priority-pill.high{background:var(--badge-danger);color:var(--badge-danger-text)}
	.mfg-dash-wrap .priority-pill.medium{background:var(--badge-warning);color:var(--badge-warning-text)}
	.mfg-dash-wrap .priority-pill.low{background:var(--badge-info);color:var(--badge-info-text)}
	.mfg-dash-wrap .progress-bar{width:100px;height:6px;background:var(--bg-tab);border-radius:var(--radius-full);overflow:hidden;display:inline-block}
	.mfg-dash-wrap .progress-bar .progress-fill{height:100%;border-radius:var(--radius-full);background:var(--kpi-gradient-2);transition:width 0.6s ease}
	.mfg-dash-wrap .progress-bar .progress-fill.blue{background:var(--kpi-gradient-1)}
	.mfg-dash-wrap .progress-bar .progress-fill.purple{background:var(--kpi-gradient-3)}
	.mfg-dash-wrap .progress-bar .progress-fill.red{background:var(--kpi-gradient-4)}
	.mfg-dash-wrap .progress-bar .progress-fill.teal{background:var(--kpi-gradient-2)}
	.mfg-dash-wrap .sidebar{display:flex;flex-direction:column;gap:20px}
	.mfg-dash-wrap .sidebar-card{background:var(--bg-card);border-radius:var(--radius-md);border:1px solid var(--border-color);padding:20px;box-shadow:var(--shadow-sm);transition:var(--transition)}
	.mfg-dash-wrap .sidebar-card:hover{box-shadow:var(--shadow-md)}
	.mfg-dash-wrap .sidebar-card .sidebar-title{font-size:13px;font-weight:600;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:14px;display:flex;align-items:center;justify-content:space-between}
	.mfg-dash-wrap .sidebar-card .sidebar-title a{font-size:12px;font-weight:500;color:var(--text-muted);text-decoration:none;text-transform:none;letter-spacing:0}
	.mfg-dash-wrap .sidebar-card .sidebar-title a:hover{color:var(--text-primary)}
	.mfg-dash-wrap .chart-placeholder{display:flex;align-items:flex-end;gap:8px;height:100px;padding-top:8px}
	.mfg-dash-wrap .chart-placeholder .bar{flex:1;border-radius:4px 4px 0 0;min-height:8px;transition:var(--transition);background:var(--chart-bar-1);position:relative}
	.mfg-dash-wrap .chart-placeholder .bar:nth-child(2){background:var(--chart-bar-2)}
	.mfg-dash-wrap .chart-placeholder .bar:nth-child(3){background:var(--chart-bar-3)}
	.mfg-dash-wrap .chart-placeholder .bar:nth-child(4){background:var(--chart-bar-4)}
	.mfg-dash-wrap .chart-placeholder .bar:nth-child(5){background:var(--chart-bar-3)}
	.mfg-dash-wrap .chart-placeholder .bar:nth-child(6){background:var(--chart-bar-2)}
	.mfg-dash-wrap .chart-placeholder .bar:nth-child(7){background:var(--chart-bar-1)}
	.mfg-dash-wrap .chart-placeholder .bar:nth-child(8){background:var(--chart-bar-4)}
	.mfg-dash-wrap .chart-placeholder .bar:nth-child(9){background:var(--chart-bar-3)}
	.mfg-dash-wrap .chart-placeholder .bar:nth-child(10){background:var(--chart-bar-2)}
	.mfg-dash-wrap .chart-labels{display:flex;justify-content:space-between;font-size:10px;color:var(--text-muted);margin-top:4px;padding:0 2px}
	.mfg-dash-wrap .text-muted{color:var(--text-muted);font-size:12px}
	.mfg-dash-wrap .branch-menu{position:absolute;top:calc(100% + 8px);left:0;background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-sm);box-shadow:var(--shadow-md);padding:6px;min-width:160px;display:none;z-index:100}
	.mfg-dash-wrap .branch-menu.open{display:block;animation:fadeSlide 0.2s ease}
	.mfg-dash-wrap .branch-menu-item{padding:8px 12px;border-radius:6px;font-size:13px;cursor:pointer;color:var(--text-primary);transition:var(--transition)}
	.mfg-dash-wrap .branch-menu-item:hover{background:var(--bg-tab)}
	.mfg-dash-wrap .branch-menu-item.active{background:var(--text-primary);color:#fff}
	.mfg-dash-wrap .filter-wrap{position:relative}
	.mfg-dash-wrap .empty-state{text-align:center;padding:40px 20px;color:var(--text-muted);font-size:14px}
	.mfg-dash-wrap .empty-state i{font-size:32px;margin-bottom:12px;display:block;opacity:0.5}
	@media(max-width:1200px){}
	@media(max-width:992px){.mfg-dash-wrap .header-glass{flex-direction:column;align-items:stretch;gap:12px;padding:18px 20px}.mfg-dash-wrap .header-center{justify-content:flex-start;flex-wrap:wrap}.mfg-dash-wrap .header-right{justify-content:flex-end}.mfg-dash-wrap .kpi-grid{grid-template-columns:repeat(2,1fr)}}
	@media(max-width:768px){.mfg-dash-wrap{padding:12px}.mfg-dash-wrap .header-left h1{font-size:18px}.mfg-dash-wrap .header-left h1 span{font-size:13px;display:block;margin-left:0}.mfg-dash-wrap .header-center{flex-direction:column;align-items:stretch}.mfg-dash-wrap .kpi-grid{grid-template-columns:1fr 1fr;gap:12px}.mfg-dash-wrap .kpi-card{padding:16px}.mfg-dash-wrap .kpi-card .kpi-value{font-size:22px}.mfg-dash-wrap .tabs-pill{flex-direction:row;overflow-x:auto;flex-wrap:nowrap;padding:4px;gap:2px}.mfg-dash-wrap .tab-btn{min-width:auto;padding:8px 14px;font-size:13px;flex:0 0 auto}.mfg-dash-wrap .tab-btn .tab-badge{display:none}.mfg-dash-wrap .table-card .table-header{flex-direction:column;align-items:stretch;gap:8px}.mfg-dash-wrap .table-card .table-header .actions{flex-wrap:wrap}}
	@media(max-width:480px){.mfg-dash-wrap .kpi-grid{grid-template-columns:1fr}.mfg-dash-wrap .header-left .logo-icon{width:36px;height:36px;font-size:18px}.mfg-dash-wrap .header-glass{padding:14px 16px}.mfg-dash-wrap .header-left h1{font-size:16px}}
	</style>`;

	if (!$('#mfg-dash-css').length) {
		$('head').append(page_css);
	}

	// =========================================================
	// HTML SHELL
	// =========================================================
	var page_html = `
	<div class="mfg-dash-wrap">
		<div class="dashboard">
			<header class="header-glass">
				<div class="header-effects"></div>
				<div class="header-left"><div class="logo-icon"><i class="fas fa-cubes"></i></div><h1>Steelstrong Valves <span>Manufacturing Dashboard</span></h1></div>
				<div class="header-center">
					<div class="filter-wrap">
						<div class="filter-chip" id="mfg-branch-chip" onclick="window.mfgToggleBranch()">
							<i class="fas fa-building"></i> <span id="mfg-branch-label">All</span> <i class="fas fa-chevron-down"></i>
						</div>
						<div class="branch-menu" id="mfg-branch-menu">
							<div class="branch-menu-item active" data-branch="All" onclick="window.mfgSelectBranch('All')">All Branches</div>
						</div>
					</div>
					<div class="filter-chip" style="padding:4px 12px;gap:4px">
						<i class="fas fa-calendar-alt"></i> 
						<input type="date" id="mfg-from-date" style="background:transparent;border:none;color:inherit;font-family:inherit;font-size:12px;outline:none" onchange="window.mfgDateChange()">
						<span>-</span>
						<input type="date" id="mfg-to-date" style="background:transparent;border:none;color:inherit;font-family:inherit;font-size:12px;outline:none" onchange="window.mfgDateChange()">
					</div>
				</div>
				<div class="header-right">
					<div class="theme-toggle" id="mfg-theme-toggle" title="Toggle theme">
						<i class="fas fa-moon"></i><i class="fas fa-sun"></i><span>Theme</span>
					</div>
					<div class="icon-btn"><i class="fas fa-bell"></i><span class="badge-dot"></span></div>
				</div>
			</header>
			<div class="kpi-grid" id="mfg-kpi-grid"></div>
			<div class="main-layout">
				<div class="content-area">
					<div class="tabs-pill" role="tablist">
						<button class="tab-btn active" data-tab="tab-bom" role="tab"><i class="fas fa-cubes"></i> BOM <span class="tab-badge" id="badge-bom">0</span></button>
						<button class="tab-btn" data-tab="tab-production" role="tab"><i class="fas fa-microchip"></i> Production <span class="tab-badge" id="badge-production">0</span></button>
						<button class="tab-btn" data-tab="tab-workorder" role="tab"><i class="fas fa-clipboard-list"></i> Work Order <span class="tab-badge" id="badge-workorder">0</span></button>
						<button class="tab-btn" data-tab="tab-material" role="tab"><i class="fas fa-boxes"></i> Material Request <span class="tab-badge" id="badge-material">0</span></button>
					</div>
					<section id="tab-bom" class="tab-panel active" role="tabpanel">
						<div class="table-card">
							<div class="table-header"><div class="title"><i class="fas fa-cubes"></i> Bill of Materials</div><div class="actions"><button onclick="window.mfgExport('bom')"><i class="fas fa-file-export"></i> Export</button><button class="btn-primary" onclick="window.mfgNewBOM()"><i class="fas fa-plus"></i> New BOM</button></div></div>
							<div class="table-scroll"><table id="table-bom"><thead><tr><th>BOM Code</th><th>Product</th><th>Version</th><th>Components</th><th>Status</th><th>Last Updated</th></tr></thead><tbody></tbody></table></div>
							<div style="padding:12px 20px;border-top:1px solid var(--border-color)"><span class="text-muted" id="footer-bom">Loading...</span></div>
						</div>
					</section>
					<section id="tab-production" class="tab-panel" role="tabpanel">
						<div class="table-card">
							<div class="table-header"><div class="title"><i class="fas fa-microchip"></i> Production Overview</div><div class="actions"><button onclick="window.mfgExport('production')"><i class="fas fa-file-export"></i> Export</button><button class="btn-primary" onclick="window.mfgStartRun()"><i class="fas fa-play"></i> Start Run</button></div></div>
							<div class="table-scroll"><table id="table-production"><thead><tr><th>Plan ID</th><th>Product</th><th>Shift</th><th>Progress</th><th>Actual / Planned</th><th>Status</th></tr></thead><tbody></tbody></table></div>
							<div style="padding:12px 20px;border-top:1px solid var(--border-color)"><span class="text-muted" id="footer-production">Loading...</span></div>
						</div>
					</section>
					<section id="tab-workorder" class="tab-panel" role="tabpanel">
						<div class="table-card">
							<div class="table-header"><div class="title"><i class="fas fa-clipboard-list"></i> Work Orders</div><div class="actions"><button onclick="window.mfgExport('workorder')"><i class="fas fa-file-export"></i> Export</button><button class="btn-primary" onclick="window.mfgNewWO()"><i class="fas fa-plus"></i> Create Order</button></div></div>
							<div class="table-scroll"><table id="table-workorder"><thead><tr><th>WO #</th><th>Product</th><th>Qty</th><th>Priority</th><th>Due Date</th><th>Status</th></tr></thead><tbody></tbody></table></div>
							<div style="padding:12px 20px;border-top:1px solid var(--border-color)"><span class="text-muted" id="footer-workorder">Loading...</span></div>
						</div>
					</section>
					<section id="tab-material" class="tab-panel" role="tabpanel">
						<div class="table-card">
							<div class="table-header"><div class="title"><i class="fas fa-boxes"></i> Material Requests</div><div class="actions"><button onclick="window.mfgExport('material')"><i class="fas fa-file-export"></i> Export</button><button class="btn-primary" onclick="window.mfgNewMR()"><i class="fas fa-plus"></i> New Request</button></div></div>
							<div class="table-scroll"><table id="table-material"><thead><tr><th>Req #</th><th>Material</th><th>Qty</th><th>Department</th><th>Date</th><th>Status</th></tr></thead><tbody></tbody></table></div>
							<div style="padding:12px 20px;border-top:1px solid var(--border-color)"><span class="text-muted" id="footer-material">Loading...</span></div>
						</div>
					</section>
				</div>
			</div>
			<div style="display:flex;justify-content:space-between;align-items:center;padding-top:8px;border-top:1px solid var(--border-color);margin-top:8px;">
				<span class="text-muted" style="font-size:13px;"> 2026 Steelstrong Valves - ERPNext Live</span>
				<span class="text-muted" style="font-size:13px;display:flex;gap:16px;">
					<span><i class="fas fa-circle" style="color:#22c55e;font-size:8px;margin-right:4px;"></i> <span id="systemStatus">All systems nominal</span></span>
					<span><i class="far fa-clock"></i> <span id="utcTime">--:-- UTC</span></span>
				</span>
			</div>
		</div>
	</div>`;

	$(page.main).html(page_html);

	// =========================================================
	// STATE & HELPERS
	// =========================================================
	var DASH_STATE = { 
		currentBranch: 'All', 
		currentTab: 'tab-bom', 
		from_date: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		to_date: frappe.datetime.get_today(),
		data: null 
	};

	function fmtDate(d) {
		if (!d) return '-';
		var dt = new Date(d);
		return dt.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
	}

	function statusClass(s) {
		s = (s || '').toLowerCase();
		if (s === 'active' || s === 'approved' || s === 'completed' || s === 'on target' || s === 'transferred') return 'success';
		if (s === 'review' || s === 'pending' || s === 'below target' || s === 'shipped') return 'warning';
		if (s === 'inactive' || s === 'rejected' || s === 'off target' || s === 'overdue') return 'danger';
		if (s === 'draft' || s === 'in progress' || s === 'in process') return 'info';
		return 'neutral';
	}

	function statusIcon(s) {
		s = (s || '').toLowerCase();
		if (s === 'active' || s === 'approved' || s === 'completed' || s === 'on target' || s === 'transferred') return 'fa-check';
		if (s === 'review' || s === 'pending' || s === 'below target') return 'fa-clock';
		if (s === 'inactive' || s === 'rejected' || s === 'off target' || s === 'overdue') return 'fa-times';
		if (s === 'draft' || s === 'in progress' || s === 'in process') return 'fa-spinner';
		if (s === 'shipped') return 'fa-truck';
		return 'fa-circle';
	}

	function filterByBranch(arr) {
		if (!arr) return [];
		return DASH_STATE.currentBranch === 'All' ? arr : arr.filter(function(x) { return x.branch === DASH_STATE.currentBranch; });
	}

	// =========================================================
	// RENDERERS
	// =========================================================
	function renderKPIs() {
		var fb = filterByBranch(DASH_STATE.data.boms);
		var fp = filterByBranch(DASH_STATE.data.production_plans);
		var fw = filterByBranch(DASH_STATE.data.work_orders);
		var fm = filterByBranch(DASH_STATE.data.material_requests);

		var completedWO = fw.filter(function(x) { return x.status === 'Completed'; }).length;
		var inProgressWO = fw.filter(function(x) { return x.status === 'In Progress' || x.status === 'In Process'; }).length;
		var totalMatQty = fm.reduce(function(a, b) { return a + (parseInt(b.qty) || 0); }, 0);
		var oee = fp.length ? Math.round(fp.reduce(function(a, b) { return a + (b.progress || 0); }, 0) / fp.length) : 0;

		var trends = [
			{ v: fb.length, p: 12, label: 'BOMs', icon: 'fa-cubes', color: 'blue' },
			{ v: fp.length, p: 5, label: 'Production Plan', icon: 'fa-microchip', color: 'teal' },
			{ v: fw.length, p: -3, label: 'Work Orders', icon: 'fa-clipboard-list', color: 'purple' },
			{ v: fm.length, p: 18, label: 'Material Requests', icon: 'fa-boxes', color: 'red' }
		];

		$('#mfg-kpi-grid').html(trends.map(function(t) {
			var trendCls = t.p > 0 ? 'up' : t.p < 0 ? 'down' : 'neutral';
			var trendIcon = t.p > 0 ? 'fa-arrow-up' : t.p < 0 ? 'fa-arrow-down' : 'fa-minus';
			return '<div class="kpi-card"><div class="kpi-top"><div class="kpi-icon ' + t.color + '"><i class="fas ' + t.icon + '"></i></div><span class="kpi-trend ' + trendCls + '"><i class="fas ' + trendIcon + '"></i> ' + (t.p > 0 ? '+' : '') + t.p + '%</span></div><div class="kpi-label">' + t.label + '</div><div class="kpi-value">' + t.v.toLocaleString() + '</div></div>';
		}).join(''));

	}

	function renderBOM() {
		var data = filterByBranch(DASH_STATE.data.boms);
		$('#badge-bom').text(data.length);
		var $tbody = $('#table-bom tbody');
		if (!data.length) {
			$tbody.html('<tr><td colspan="6"><div class="empty-state"><i class="fas fa-cubes"></i>No BOM records for this branch</div></td></tr>');
		} else {
			$tbody.html(data.map(function(r) {
				return `<tr onclick="frappe.set_route('Form', 'BOM', '${r.name}')">` + '<td><strong>' + r.name + '</strong></td><td>' + (r.item_name || r.item_code || '') + '</td><td>v' + (r.version || '001') + '</td><td>' + (r.components || 1) + '</td><td><span class="status-pill ' + statusClass(r.status) + '"><i class="fas ' + statusIcon(r.status) + '"></i> ' + r.status + '</span></td><td>' + fmtDate(r.last_updated) + '</td></tr>';
			}).join(''));
		}
		$('#footer-bom').text('Showing ' + data.length + ' of ' + DASH_STATE.data.boms.length + ' BOM records');
	}

	function renderProduction() {
		var data = filterByBranch(DASH_STATE.data.production_plans);
		$('#badge-production').text(data.length);
		var $tbody = $('#table-production tbody');
		if (!data.length) {
			$tbody.html('<tr><td colspan="6"><div class="empty-state"><i class="fas fa-microchip"></i>No production plans for this branch</div></td></tr>');
		} else {
			$tbody.html(data.map(function(r) {
				var barColor = 'teal';
				if (r.progress < 40) barColor = 'red';
				else if (r.progress < 75) barColor = 'blue';
				else if (r.progress < 100) barColor = 'purple';
				return `<tr onclick="frappe.set_route('Form', 'Production Plan', '${r.name}')">` + '<td><strong>' + r.name + '</strong></td><td>' + (r.product || r.name) + '</td><td>' + (r.shift || '1st') + '</td><td><div class="progress-bar"><div class="progress-fill ' + barColor + '" style="width:' + r.progress + '%"></div></div></td><td>' + r.actual + ' / ' + r.target + '</td><td><span class="status-pill ' + statusClass(r.status) + '"><i class="fas ' + statusIcon(r.status) + '"></i> ' + r.status + '</span></td></tr>';
			}).join(''));
		}
		$('#footer-production').text('Last updated: just now');
	}

	function renderWorkOrders() {
		var data = filterByBranch(DASH_STATE.data.work_orders);
		$('#badge-workorder').text(data.length);
		var $tbody = $('#table-workorder tbody');
		if (!data.length) {
			$tbody.html('<tr><td colspan="6"><div class="empty-state"><i class="fas fa-clipboard-list"></i>No work orders for this branch</div></td></tr>');
		} else {
			$tbody.html(data.map(function(r) {
				return `<tr onclick="frappe.set_route('Form', 'Work Order', '${r.name}')">` + '<td><strong>' + r.name + '</strong></td><td>' + (r.product || r.item_name || r.production_item || r.name) + '</td><td>' + (r.qty || 0) + '</td><td><span class="priority-pill ' + (r.priority || 'medium').toLowerCase() + '">' + (r.priority || 'Medium') + '</span></td><td>' + fmtDate(r.due_date) + '</td><td><span class="status-pill ' + statusClass(r.status) + '"><i class="fas ' + statusIcon(r.status) + '"></i> ' + r.status + '</span></td></tr>';
			}).join(''));
		}
		$('#footer-workorder').text('Showing ' + data.length + ' of ' + DASH_STATE.data.work_orders.length + ' work orders');
	}

	function renderMaterialRequests() {
		var data = filterByBranch(DASH_STATE.data.material_requests);
		$('#badge-material').text(data.length);
		var $tbody = $('#table-material tbody');
		if (!data.length) {
			$tbody.html('<tr><td colspan="6"><div class="empty-state"><i class="fas fa-boxes"></i>No material requests for this branch</div></td></tr>');
		} else {
			$tbody.html(data.map(function(r) {
				return `<tr onclick="frappe.set_route('Form', 'Material Request', '${r.name}')">` + '<td><strong>' + r.name + '</strong></td><td>' + (r.material || r.title || r.name) + '</td><td>' + (r.qty || '1 Nos') + '</td><td>' + (r.department || 'Stores') + '</td><td>' + fmtDate(r.date || r.transaction_date) + '</td><td><span class="status-pill ' + statusClass(r.status) + '"><i class="fas ' + statusIcon(r.status) + '"></i> ' + r.status + '</span></td></tr>';
			}).join(''));
		}
		$('#footer-material').text('Showing ' + data.length + ' of ' + DASH_STATE.data.material_requests.length + ' material requests');
	}

	function renderChart() {
		// Removed chart rendering as sidebar is removed
	}

	function updateSystemStatus() {
		var fw = filterByBranch(DASH_STATE.data.work_orders);
		var overdue = fw.filter(function(x) { return x.status === 'Overdue'; }).length;
		var el = document.getElementById('systemStatus');
		if (overdue > 0) {
			el.innerHTML = '<span style="color:var(--badge-danger-text)">' + overdue + ' Work Order(s) Overdue</span>';
		} else {
			el.textContent = 'All systems nominal';
		}
	}

	function renderAll() {
		if (!DASH_STATE.data) return;
		renderKPIs();
		renderBOM();
		renderProduction();
		renderWorkOrders();
		renderMaterialRequests();
		renderChart();
		updateSystemStatus();
	}

	// =========================================================
	// DATA LOADING
	// =========================================================
	function loadData() {
		frappe.call({
			method: 'generate_item.generate_item.page.manufacturing_dashbo.manufacturing_dashbo.get_dashboard_data',
			args: { 
				branch: DASH_STATE.currentBranch,
				from_date: DASH_STATE.from_date,
				to_date: DASH_STATE.to_date
			},
			callback: function(r) {
				if (r.message) {
					DASH_STATE.data = r.message;
					renderAll();
				} else {
					frappe.show_alert({ message: __('No data returned from server'), indicator: 'orange' });
				}
			},
			error: function(err) {
				frappe.show_alert({ message: __('Failed to load dashboard data'), indicator: 'red' });
				console.error(err);
			}
		});
	}

	// =========================================================
	// EVENT HANDLERS (exposed to window for inline onclick)
	// =========================================================
	window.mfgToggleBranch = function() {
		$('#mfg-branch-menu').toggleClass('open');
	};

	window.mfgSelectBranch = function(branch) {
		DASH_STATE.currentBranch = branch;
		$('#mfg-branch-label').text(branch === 'All' ? 'All Branches' : branch);
		$('.branch-menu-item').removeClass('active');
		$('.branch-menu-item[data-branch="' + branch + '"]').addClass('active');
		$('#mfg-branch-menu').removeClass('open');
		loadData();
	};

	window.mfgDateChange = function() {
		DASH_STATE.from_date = $('#mfg-from-date').val();
		DASH_STATE.to_date = $('#mfg-to-date').val();
		loadData();
	};

	window.mfgExport = function(type) {
		frappe.show_alert({ message: __('Export ' + type + ' - integrate with ERPNext report builder'), indicator: 'blue' });
	};

	window.mfgNewBOM = function() {
		frappe.new_doc('BOM');
	};

	window.mfgStartRun = function() {
		frappe.new_doc('Production Plan');
	};

	window.mfgNewWO = function() {
		frappe.new_doc('Work Order');
	};

	window.mfgNewMR = function() {
		frappe.new_doc('Material Request');
	};

	// Tabs
	$('.tabs-pill').on('click', '.tab-btn', function() {
		var tabId = $(this).data('tab');
		if (!tabId) return;
		$('.tab-btn').removeClass('active');
		$('.tab-panel').removeClass('active');
		$(this).addClass('active');
		$('#' + tabId).addClass('active');
		DASH_STATE.currentTab = tabId;
	});

	// Theme toggle
	$('#mfg-theme-toggle').on('click', function() {
		var html = document.documentElement;
		var current = html.getAttribute('data-theme');
		if (current === 'dark') {
			html.removeAttribute('data-theme');
			localStorage.setItem('theme', 'light');
		} else {
			html.setAttribute('data-theme', 'dark');
			localStorage.setItem('theme', 'dark');
		}
	});

	// Restore theme
	var savedTheme = localStorage.getItem('theme');
	if (savedTheme === 'dark') {
		document.documentElement.setAttribute('data-theme', 'dark');
	}

	// Close branch menu on outside click
	$(document).on('click', function(e) {
		if (!$(e.target).closest('.filter-wrap').length) {
			$('#mfg-branch-menu').removeClass('open');
		}
	});

	// UTC clock
	setInterval(function() {
		var now = new Date();
		$('#utcTime').text(now.toISOString().substr(11, 5) + ' UTC');
	}, 1000);

	// Initial load
	$('#mfg-from-date').val(DASH_STATE.from_date);
	$('#mfg-to-date').val(DASH_STATE.to_date);

	frappe.call({
		method: 'generate_item.generate_item.page.manufacturing_dashbo.manufacturing_dashbo.get_branches',
		callback: function(r) {
			if (r.message) {
				var menu = $('#mfg-branch-menu');
				var html = '<div class="branch-menu-item active" data-branch="All" onclick="window.mfgSelectBranch(\'All\')">All Branches</div>';
				r.message.forEach(function(branch) {
					html += '<div class="branch-menu-item" data-branch="' + branch + '" onclick="window.mfgSelectBranch(\'' + branch + '\')">' + branch + '</div>';
				});
				menu.html(html);
				// Check if Sanand exists and select it default if we want, but let's stick to 'All' by default
			}
			loadData();
		}
	});
};
