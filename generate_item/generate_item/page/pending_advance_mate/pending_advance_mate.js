frappe.pages['pending-advance-mate'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Pending Advance Material Request'),
		single_column: true,
	});

	new PendingAdvanceMaterialRequestPage({
		wrapper: wrapper,
		page: page,
	});
};

class PendingAdvanceMaterialRequestPage {
	constructor({ wrapper, page }) {
		this.wrapper = wrapper;
		this.page = page;
		this.pending_changes = {};
		this.current_data = [];
		this.active_editor = null;
		this.active_row_name = null;
		this.dropdown_container = null;
		this.row_counter = 0;
		this.columns = [
			{ id: 'sr_no', name: __('Sr No'), width: 70 },
			{ id: 'material_request', name: __('Material Request'), width: 180 },
			{ id: 'transaction_date', name: __('Date'), width: 110 },
			{ id: 'company', name: __('Company'), width: 180 },
			{ id: 'item_code', name: __('Item'), width: 160 },
			{ id: 'item_name', name: __('Item Name'), width: 260 },
			{ id: 'qty', name: __('Qty'), width: 100 },
			{ id: 'warehouse', name: __('Warehouse'), width: 200 },
			{ id: 'batch_no', name: __('Batch No'), width: 150 },
			{ id: 'production_plan', name: __('Production Plan'), width: 200 },
		];

		this.setup_dropdown_container();
		$("<style>")
			.prop("type", "text/css")
			.html(`
				.awesomplete > ul,
				.ui-autocomplete,
				.ui-front {
					z-index: 100000 !important;
				}
			`)
			.appendTo("head");

		this.setup_filters();
		this.setup_toolbar();
		this.setup_container();
		this.setup_global_click_handler();
		this.refresh();
	}

	setup_dropdown_container() {
		this.dropdown_container = document.createElement('div');
		this.dropdown_container.id = 'pp-autocomplete-dropdown';
		this.dropdown_container.style.cssText = `
			position: fixed;
			z-index: 99999;
			display: none;
			background: white;
			border: 1px solid #d1d5db;
			border-radius: 6px;
			box-shadow: 0 10px 25px rgba(0,0,0,0.15);
			max-height: 250px;
			overflow-y: auto;
			min-width: 200px;
		`;
		document.body.appendChild(this.dropdown_container);
	}

	setup_filters() {
		this.company_field = this.page.add_field({
			fieldname: 'company',
			label: __('Company'),
			fieldtype: 'Link',
			options: 'Company',
			default: frappe.defaults.get_user_default("company"),
			change: () => this.refresh(),
		});

		this.from_date_field = this.page.add_field({
			fieldname: 'from_date',
			label: __('From Date'),
			fieldtype: 'Date',
			change: () => this.refresh(),
		});

		this.to_date_field = this.page.add_field({
			fieldname: 'to_date',
			label: __('To Date'),
			fieldtype: 'Date',
			change: () => this.refresh(),
		});
	}

	get_filters() {
		return {
			company: this.company_field.get_value(),
			from_date: this.from_date_field.get_value(),
			to_date: this.to_date_field.get_value(),
		};
	}

	setup_toolbar() {
		this.page.set_primary_action(__('Refresh'), () => this.refresh());

		this.save_btn = this.page.add_inner_button(__('Save Changes'), () => {
			this.save_all_changes();
		});
		this.update_save_button();

		this.page.add_inner_button(__('Export CSV'), () => {
			this.export_csv();
		});
	}

	update_save_button() {
		if (!this.save_btn) return;
		const count = Object.keys(this.pending_changes).length;
		if (count > 0) {
			this.save_btn.html(`<i class="fa fa-save mr-1"></i>${__('Save Changes')} (${count})`);
			this.save_btn.removeClass('btn-default').addClass('btn-warning');
		} else {
			this.save_btn.html(__('Save Changes'));
			this.save_btn.removeClass('btn-warning').addClass('btn-default');
		}
	}

	setup_container() {
		this.table_container = document.createElement('div');
		this.table_container.style.height = 'calc(100vh - 200px)';
		this.table_container.style.overflow = 'auto';
		this.table_container.style.position = 'relative';
		this.page.main.append(this.table_container);
	}

	setup_global_click_handler() {
		document.addEventListener('click', (e) => {
			const target = e.target;
			const isInput = target.closest('.pp-input');
			const isDropdown = target.closest('#pp-autocomplete-dropdown');
			const isEditableCell = target.closest('.pp-editable-cell');
			
			if (!isInput && !isDropdown) {
				this.close_dropdown();
				if (!isEditableCell) {
					this.commit_editor();
				}
			}
		});
	}

	refresh() {
		this.commit_editor();
		this.close_dropdown();
		this.load_data().then((data) => {
			this.current_data = data;
			this.row_counter = 0;
			this.render_table();
		});
	}

	load_data() {
		return frappe
			.call({
				method: 'generate_item.generate_item.page.pending_advance_mate.pending_advance_mate.get_data',
				args: { filters: this.get_filters() },
			})
			.then((r) => r.message || []);
	}

	render_table() {
		this.table_container.innerHTML = '';

		if (!this.current_data.length) {
			this.table_container.innerHTML = `
				<div style="text-align:center;padding:60px 20px;color:var(--text-muted);">
					<div style="font-size:48px;margin-bottom:16px;"><i class="fa fa-search"></i></div>
					<div style="font-size:14px;">${__('No records found')}</div>
				</div>`;
			return;
		}

		const table = document.createElement('table');
		table.className = 'table table-bordered table-hover';
		table.style.cssText = 'margin:0;background:white;border-collapse:collapse;width:100%;';

		const thead = document.createElement('thead');
		thead.style.cssText = 'position:sticky;top:0;z-index:10;background:#f8fafc;';
		const headerRow = document.createElement('tr');
		this.columns.forEach((col) => {
			const th = document.createElement('th');
			th.style.cssText = `padding:10px 12px;font-size:12px;font-weight:600;color:#475569;border-bottom:2px solid #e2e8f0;min-width:${col.width}px;white-space:nowrap;`;
			th.textContent = col.name;
			headerRow.appendChild(th);
		});
		thead.appendChild(headerRow);
		table.appendChild(thead);

		const tbody = document.createElement('tbody');
		this.current_data.forEach((row) => {
			this.row_counter++;
			const tr = document.createElement('tr');
			tr.style.cssText = 'transition:background 0.15s;';
			tr.addEventListener('mouseenter', () => { tr.style.background = '#f1f5f9'; });
			tr.addEventListener('mouseleave', () => { tr.style.background = ''; });

			this.columns.forEach((col) => {
				const td = document.createElement('td');
				td.style.cssText = 'padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px;';

				if (col.id === 'sr_no') {
					td.innerHTML = `<span style="color:#6b7280;font-weight:500;">${this.row_counter}</span>`;
				} else if (col.id === 'production_plan') {
					td.className = 'pp-editable-cell';
					td.style.cursor = 'pointer';
					td.setAttribute('data-row-name', row.name);
					td.setAttribute('data-batch-no', row.batch_no || '');
					this.render_pp_cell(td, row);
					td.addEventListener('click', (e) => {
						e.stopPropagation();
						this.make_pp_editable(td, row);
					});
				} else if (col.id === 'batch_no') {
					td.setAttribute('data-row-name', row.name);
					if (!row.batch_no) {
						td.className = 'pp-editable-cell';
						td.style.cursor = 'pointer';
					}
					this.render_batch_cell(td, row);
					td.addEventListener('click', (e) => {
						e.stopPropagation();
						if (!row.batch_no) {
							this.make_batch_editable(td, row);
						}
					});
				} else {
					td.innerHTML = this.format_cell_value(col.id, row[col.id], row);
				}

				tr.appendChild(td);
			});

			tbody.appendChild(tr);
		});

		table.appendChild(tbody);
		this.table_container.appendChild(table);
	}

	format_cell_value(fieldname, value, row) {
		const escaped = frappe.utils.escape_html(value || '');
		
		if (fieldname === 'material_request') {
			return `<a href="/app/material-request/${escaped}" target="_blank" style="color:#1e293b;font-weight:600;text-decoration:none;">${escaped}</a>`;
		}
		if (fieldname === 'company') {
			return `<a href="/app/company/${escaped}" target="_blank" style="color:#1e293b;font-weight:500;text-decoration:none;">${escaped}</a>`;
		}
		if (fieldname === 'item_code') {
			return `<a href="/app/item/${escaped}" target="_blank" style="color:#1e293b;font-weight:500;text-decoration:none;">${escaped}</a>`;
		}
		if (fieldname === 'batch_no' && value) {
			return `<a href="/app/batch/${escaped}" target="_blank" style="color:#1e293b;font-weight:500;text-decoration:none;">${escaped}</a>`;
		}
		if (fieldname === 'warehouse') {
			return `<a href="/app/warehouse/${escaped}" target="_blank" style="color:#1e293b;font-weight:500;text-decoration:none;">${escaped}</a>`;
		}
		if (fieldname === 'qty') {
			return `<span style="font-weight:bold;color:#dc2626;">${value || ''}</span>`;
		}
		return `<span style="color:#1e293b;">${escaped}</span>`;
	}

	render_pp_cell(td, row) {
		const ppKey = `${row.name}::production_plan`;
		const ppValue = this.pending_changes[ppKey]?.new_value ?? row.production_plan ?? '';
		const isPending = !!this.pending_changes[ppKey];

		td.innerHTML = '';
		
		if (ppValue) {
			const link = document.createElement('a');
			link.href = `/app/production-plan/${encodeURIComponent(ppValue)}`;
			link.target = '_blank';
			link.style.cssText = 'font-weight:500;color:#1e293b;text-decoration:none;';
			link.textContent = ppValue;
			link.addEventListener('click', (e) => e.stopPropagation());
			td.appendChild(link);
		} else {
			const span = document.createElement('span');
			span.style.cssText = 'color:var(--text-muted);';
			span.textContent = __('Click to add');
			td.appendChild(span);
		}

		if (isPending) {
			td.style.background = '#fef9c3';
			td.style.borderLeft = '3px solid #facc15';
			td.title = __('Unsaved — click Save Changes to apply');
		} else {
			td.style.background = '';
			td.style.borderLeft = '';
			td.title = __('Click to edit');
		}
	}

	make_pp_editable(td, row) {
		if (this.active_row_name === row.name) return;

		this.commit_editor();
		this.close_dropdown();

		if (!row.batch_no) {
			frappe.show_alert({
				message: __('Batch No is required to link Production Plan.'),
				indicator: 'red',
			}, 5);
			return;
		}

		const ppKey = `${row.name}::production_plan`;
		const currentValue = this.pending_changes[ppKey]?.new_value ?? row.production_plan ?? '';

		td.innerHTML = '';
		td.style.padding = '0';

		const input = document.createElement('input');
		input.type = 'text';
		input.className = 'pp-input form-control';
		input.value = currentValue;
		input.placeholder = __('Type to search...');
		input.style.cssText = 'width:100%;height:100%;border:2px solid #3b82f6;border-radius:4px;padding:6px 8px;font-size:13px;outline:none;color:#1e293b;';
		td.appendChild(input);

		this.active_editor = { input, td, row, currentValue, fieldname: 'production_plan' };
		this.active_row_name = row.name;

		this.search_production_plans('', row.batch_no, input, td, row);

		setTimeout(() => {
			input.focus();
		}, 50);

		let searchTimeout;
		input.addEventListener('input', () => {
			clearTimeout(searchTimeout);
			const txt = input.value.trim();
			searchTimeout = setTimeout(() => this.search_production_plans(txt, row.batch_no, input, td, row), 300);
		});

		input.addEventListener('keydown', (e) => {
			if (e.key === 'Enter') {
				e.preventDefault();
				const selectedItem = this.dropdown_container.querySelector('.pp-dropdown-item.active');
				if (selectedItem) {
					const val = selectedItem.textContent;
					input.value = val;
					this.stage_change(row, val);
				} else {
					const val = input.value.trim();
					if (val) {
						this.stage_change(row, val);
					}
				}
				this.commit_editor();
				this.close_dropdown();
			}
			if (e.key === 'Escape') {
				e.preventDefault();
				input.value = currentValue;
				this.commit_editor();
				this.close_dropdown();
			}
			if (e.key === 'ArrowDown') {
				e.preventDefault();
				this.navigate_dropdown(1);
			}
			if (e.key === 'ArrowUp') {
				e.preventDefault();
				this.navigate_dropdown(-1);
			}
			if (e.key === 'Tab') {
				e.preventDefault();
				const selectedItem = this.dropdown_container.querySelector('.pp-dropdown-item.active');
				if (selectedItem) {
					const val = selectedItem.textContent;
					input.value = val;
					this.stage_change(row, val);
				}
				this.commit_editor();
				this.close_dropdown();
			}
		});

		input.addEventListener('blur', () => {
			setTimeout(() => {
				if (this.active_editor?.input === input) {
					const val = input.value.trim();
					if (val && val !== currentValue) {
						this.stage_change(row, val);
					}
					this.commit_editor();
					this.close_dropdown();
				}
			}, 200);
		});
	}

	make_batch_editable(td, row) {
		if (this.active_row_name === row.name) return;

		this.commit_editor();
		this.close_dropdown();

		if (row.batch_no) return;

		const batchKey = `${row.name}::batch_no`;
		const currentValue = this.pending_changes[batchKey]?.new_value ?? '';

		td.innerHTML = '';
		td.style.padding = '0';

		const input = document.createElement('input');
		input.type = 'text';
		input.className = 'pp-input form-control';
		input.value = currentValue;
		input.placeholder = __('Search batch...');
		input.style.cssText = 'width:100%;height:100%;border:2px solid #3b82f6;border-radius:4px;padding:6px 8px;font-size:13px;outline:none;color:#1e293b;';
		td.appendChild(input);

		this.active_editor = { input, td, row, currentValue, fieldname: 'batch_no' };
		this.active_row_name = row.name;

		this.search_batches('', input, td, row);

		setTimeout(() => { input.focus(); }, 50);

		let searchTimeout;
		input.addEventListener('input', () => {
			clearTimeout(searchTimeout);
			const txt = input.value.trim();
			searchTimeout = setTimeout(() => this.search_batches(txt, input, td, row), 300);
		});

		input.addEventListener('keydown', (e) => {
			if (e.key === 'Enter') {
				e.preventDefault();
				const selectedItem = this.dropdown_container.querySelector('.pp-dropdown-item.active');
				if (selectedItem) {
					const val = selectedItem.textContent;
					input.value = val;
					this.stage_change(row, val, 'batch_no');
				} else {
					const val = input.value.trim();
					if (val) {
						this.stage_change(row, val, 'batch_no');
					}
				}
				this.commit_editor();
				this.close_dropdown();
			}
			if (e.key === 'Escape') {
				e.preventDefault();
				input.value = currentValue;
				this.commit_editor();
				this.close_dropdown();
			}
			if (e.key === 'ArrowDown') {
				e.preventDefault();
				this.navigate_dropdown(1);
			}
			if (e.key === 'ArrowUp') {
				e.preventDefault();
				this.navigate_dropdown(-1);
			}
			if (e.key === 'Tab') {
				e.preventDefault();
				const selectedItem = this.dropdown_container.querySelector('.pp-dropdown-item.active');
				if (selectedItem) {
					const val = selectedItem.textContent;
					input.value = val;
					this.stage_change(row, val, 'batch_no');
				}
				this.commit_editor();
				this.close_dropdown();
			}
		});

		input.addEventListener('blur', () => {
			setTimeout(() => {
				if (this.active_editor?.input === input) {
					const val = input.value.trim();
					if (val && val !== currentValue) {
						this.stage_change(row, val, 'batch_no');
					}
					this.commit_editor();
					this.close_dropdown();
				}
			}, 200);
		});
	}

	search_production_plans(txt, batch_no, input, td, row) {
		frappe.call({
			method: 'generate_item.generate_item.page.pending_advance_mate.pending_advance_mate.production_plan_query',
			args: {
				doctype: 'Production Plan',
				txt: txt || '',
				searchfield: 'name',
				start: 0,
				page_len: 50,
				filters: { batch_no: batch_no }
			},
			callback: (r) => {
				if (this.active_editor?.input !== input) return;
				
				const results = r.message || [];
				this.show_dropdown(input, results, (selectedValue) => {
					this.stage_change(row, selectedValue);
					input.value = selectedValue;
					this.commit_editor();
					this.close_dropdown();
				});
			}
		});
	}

	search_batches(txt, input, td, row) {
		frappe.call({
			method: 'generate_item.generate_item.page.pending_advance_mate.pending_advance_mate.batch_query',
			args: {
				doctype: 'Batch',
				txt: txt || '',
				searchfield: 'name',
				start: 0,
				page_len: 50,
				filters: {}
			},
			callback: (r) => {
				if (this.active_editor?.input !== input) return;

				const results = r.message || [];
				this.show_dropdown(input, results, (selectedValue) => {
					this.stage_change(row, selectedValue, 'batch_no');
					input.value = selectedValue;
					this.commit_editor();
					this.close_dropdown();
				});
			}
		});
	}

	show_dropdown(input, results, onSelect) {
		const dropdown = this.dropdown_container;
		
		if (!results.length) {
			dropdown.innerHTML = '<div style="padding:8px 12px;color:var(--text-muted);font-size:13px;">No Production Plans found for this batch</div>';
			dropdown.style.display = 'block';
			const rect = input.getBoundingClientRect();
			dropdown.style.top = `${rect.bottom + 2}px`;
			dropdown.style.left = `${rect.left}px`;
			dropdown.style.minWidth = `${rect.width}px`;
			return;
		}

		const rect = input.getBoundingClientRect();
		dropdown.style.top = `${rect.bottom + 2}px`;
		dropdown.style.left = `${rect.left}px`;
		dropdown.style.minWidth = `${rect.width}px`;
		dropdown.style.display = 'block';

		dropdown.innerHTML = '';
		results.forEach((item, index) => {
			const value = typeof item === 'string' ? item : item.value || item.name || item[0];
			const div = document.createElement('div');
			div.className = 'pp-dropdown-item';
			div.setAttribute('data-index', index);
			div.setAttribute('data-value', value);
			div.textContent = value;
			div.style.cssText = 'padding:8px 12px;cursor:pointer;font-size:13px;border-bottom:1px solid #f1f5f9;color:#1e293b;';
			
			div.addEventListener('mouseenter', () => {
				dropdown.querySelectorAll('.pp-dropdown-item').forEach(d => {
					d.style.background = '';
					d.classList.remove('active');
				});
				div.style.background = '#eff6ff';
				div.classList.add('active');
			});
			
			div.addEventListener('mousedown', (e) => {
				e.preventDefault();
				e.stopPropagation();
				onSelect(value);
			});

			dropdown.appendChild(div);
		});

		const firstItem = dropdown.querySelector('.pp-dropdown-item');
		if (firstItem) {
			firstItem.style.background = '#eff6ff';
			firstItem.classList.add('active');
		}
	}

	navigate_dropdown(direction) {
		const dropdown = this.dropdown_container;
		if (dropdown.style.display === 'none') return;

		const items = dropdown.querySelectorAll('.pp-dropdown-item');
		if (!items.length) return;

		const activeItem = dropdown.querySelector('.pp-dropdown-item.active');
		let currentIndex = -1;
		if (activeItem) {
			currentIndex = parseInt(activeItem.getAttribute('data-index'));
		}

		let newIndex = currentIndex + direction;
		if (newIndex < 0) newIndex = items.length - 1;
		if (newIndex >= items.length) newIndex = 0;

		items.forEach((item, i) => {
			item.style.background = '';
			item.classList.remove('active');
			if (i === newIndex) {
				item.style.background = '#eff6ff';
				item.classList.add('active');
				item.scrollIntoView({ block: 'nearest' });
			}
		});
	}

	close_dropdown() {
		this.dropdown_container.style.display = 'none';
		this.dropdown_container.innerHTML = '';
	}

	commit_editor() {
		if (!this.active_editor) return;

		const { td, row, fieldname } = this.active_editor;

		if (td && row) {
			td.innerHTML = '';
			td.style.padding = '8px 12px';
			if (fieldname === 'batch_no') {
				this.render_batch_cell(td, row);
			} else {
				this.render_pp_cell(td, row);
			}
		}

		this.active_editor = null;
		this.active_row_name = null;
	}

	stage_change(rowData, newValue, fieldname = 'production_plan') {
		const key = `${rowData.name}::${fieldname}`;
		const originalValue = fieldname === 'batch_no'
			? (rowData.batch_no || '')
			: (rowData.production_plan || '');

		if (newValue && newValue !== originalValue) {
			this.pending_changes[key] = {
				row_name: rowData.name,
				material_request: rowData.material_request,
				new_value: newValue,
				fieldname: fieldname,
			};
		} else {
			delete this.pending_changes[key];
		}

		this.update_save_button();
	}

	render_batch_cell(td, row) {
		const batchKey = `${row.name}::batch_no`;
		const batchValue = this.pending_changes[batchKey]?.new_value ?? row.batch_no ?? '';
		const isPending = !!this.pending_changes[batchKey];

		td.innerHTML = '';

		if (batchValue) {
			const link = document.createElement('a');
			link.href = `/app/batch/${encodeURIComponent(batchValue)}`;
			link.target = '_blank';
			link.style.cssText = 'font-weight:500;color:#1e293b;text-decoration:none;';
			link.textContent = batchValue;
			link.addEventListener('click', (e) => e.stopPropagation());
			td.appendChild(link);
		} else {
			const span = document.createElement('span');
			span.style.cssText = 'color:var(--text-muted);';
			span.textContent = __('Click to add batch');
			td.appendChild(span);
		}

		if (isPending) {
			td.style.background = '#fef9c3';
			td.style.borderLeft = '3px solid #facc15';
			td.title = __('Unsaved — click Save Changes to apply');
		} else {
			td.style.background = '';
			td.style.borderLeft = '';
			td.title = batchValue ? '' : __('Click to add batch');
		}
	}

	async save_all_changes() {
		this.commit_editor();
		this.close_dropdown();

		const changes = this.pending_changes;
		const keys = Object.keys(changes);

		if (!keys.length) {
			frappe.show_alert({ message: __('No pending changes to save.'), indicator: 'blue' }, 3);
			return;
		}

		// Group by (material_request, fieldname)
		const byMrAndField = {};
		keys.forEach((key) => {
			const change = changes[key];
			const mrFieldKey = `${change.material_request}::${change.fieldname}`;
			if (!byMrAndField[mrFieldKey]) byMrAndField[mrFieldKey] = [];
			byMrAndField[mrFieldKey].push({
				name: change.row_name,
				[change.fieldname]: change.new_value,
			});
		});

		const groups = Object.keys(byMrAndField);
		let totalUpdated = 0;

		frappe.show_alert({
			message: __('Saving {0} change(s)…', [keys.length]),
			indicator: 'blue',
		}, 2);

		for (const groupKey of groups) {
			const [mrName, fieldname] = groupKey.split('::');
			const updates = byMrAndField[groupKey];

			try {
				let method, args;
				if (fieldname === 'production_plan') {
					method = 'generate_item.generate_item.page.pending_advance_mate.pending_advance_mate.bulk_update_production_plan';
					args = { material_request: mrName, updates: updates.map(u => ({ name: u.name, production_plan: u.production_plan })) };
				} else {
					method = 'generate_item.generate_item.page.pending_advance_mate.pending_advance_mate.bulk_update_batch';
					args = { material_request: mrName, updates: updates.map(u => ({ name: u.name, batch_no: u.batch_no })) };
				}

				const r = await frappe.call({ method, args });
				if (r.message) totalUpdated += r.message.updated || 0;
			} catch (err) {
				console.error('Save failed for:', mrName, fieldname, err);
				frappe.show_alert({
					message: __('Failed to save for {0} ({1})', [mrName, fieldname]),
					indicator: 'red',
				}, 5);
			}
		}

		this.pending_changes = {};
		this.update_save_button();

		frappe.show_alert({
			message: totalUpdated > 0
				? __('Saved — {0} item(s) updated.', [totalUpdated])
				: __('No items were updated.'),
			indicator: totalUpdated > 0 ? 'green' : 'orange',
		}, 5);

		this.refresh();
	}

	export_csv() {
		if (!this.current_data || !this.current_data.length) {
			frappe.show_alert({ message: __('No data to export.'), indicator: 'orange' }, 3);
			return;
		}

		const exportColumns = this.columns.filter(col => col.id !== 'sr_no');
		const headers = exportColumns.map((col) => `"${col.name}"`).join(',');
		
		const rows = this.current_data.map((row) => {
			const ppKey = `${row.name}::production_plan`;
			const batchKey = `${row.name}::batch_no`;
			const ppValue = this.pending_changes[ppKey]?.new_value ?? row.production_plan ?? '';
			const batchValue = this.pending_changes[batchKey]?.new_value ?? row.batch_no ?? '';
			return exportColumns.map((col) => {
				let val;
				if (col.id === 'production_plan') {
					val = ppValue;
				} else if (col.id === 'batch_no') {
					val = batchValue;
				} else {
					val = (row[col.id] ?? '');
				}
				val = String(val).replace(/"/g, '""');
				return `"${val}"`;
			}).join(',');
		});

		const csv = headers + '\n' + rows.join('\n');
		const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
		const url = URL.createObjectURL(blob);
		const link = document.createElement('a');
		link.href = url;
		link.download = `pending_advance_material_request_${frappe.datetime.now_datetime()}.csv`;
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
		URL.revokeObjectURL(url);
	}
}