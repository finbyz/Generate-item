frappe.pages['sales-performance-da'].on_page_load = function (wrapper) {

    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Sales Performance Dashboard',
        single_column: true
    });

    // Add Chart.js CDN
    if (!window.Chart) {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js';
        document.head.appendChild(script);
    }

    const from_date = page.add_field({
        label: 'From Date',
        fieldtype: 'Date',
        default: frappe.datetime.month_start(),
        change: load_data
    });

    const to_date = page.add_field({
        label: 'To Date',
        fieldtype: 'Date',
        default: frappe.datetime.get_today(),
        change: load_data
    });

    const branch = page.add_field({
        label: 'Branch',
        fieldtype: 'Link',
        options: 'Branch',
        change: load_data
    });

    // Add CSS styles
    const styles = `
        <style>
            .dashboard-container {
                padding: 20px;
            }
            .dashboard-row {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }
            .chart-card {
                background: var(--card-bg);
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                border: 1px solid var(--border-color);
            }
            .chart-card h3 {
                margin: 0 0 15px 0;
                font-size: 16px;
                font-weight: 600;
                color: var(--heading-color);
            }
            .chart-wrapper {
                position: relative;
                height: 280px;
            }
            .value-cards-section {
                margin-bottom: 20px;
            }
            .value-cards-section h4 {
                margin: 0 0 12px 0;
                font-size: 14px;
                font-weight: 600;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .value-cards-row {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 15px;
            }
            .value-card {
                background: linear-gradient(135deg, var(--card-bg), var(--control-bg));
                border-radius: 10px;
                padding: 18px;
                border: 1px solid var(--border-color);
                text-align: center;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .value-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
            .value-card .label {
                font-size: 12px;
                color: var(--text-muted);
                margin-bottom: 6px;
                text-transform: uppercase;
                letter-spacing: 0.3px;
            }
            .value-card .value {
                font-size: 24px;
                font-weight: 700;
                color: var(--primary);
            }
            .value-card .unit {
                font-size: 12px;
                color: var(--text-muted);
                margin-top: 4px;
            }
            .value-card.fy { border-left: 4px solid #2E7D32; }
            .value-card.month { border-left: 4px solid #1565C0; }
            .value-card.outstanding { border-left: 4px solid #EF6C00; }
            .value-card.collected { border-left: 4px solid #7B1FA2; }
            .value-card.warning { border-left: 4px solid #F44336; background: linear-gradient(135deg, #FFF3E0, #FFECB3); }
            
            .bom-section {
                background: var(--card-bg);
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                border: 1px solid var(--border-color);
                margin-bottom: 20px;
            }
            .bom-section h4 {
                margin: 0 0 15px 0;
                font-size: 16px;
                font-weight: 600;
                color: var(--heading-color);
            }
            .bom-summary {
                display: flex;
                gap: 20px;
                margin-bottom: 15px;
            }
            .bom-summary .stat {
                background: #FFF3E0;
                padding: 12px 20px;
                border-radius: 8px;
                border-left: 4px solid #F44336;
            }
            .bom-summary .stat .num {
                font-size: 20px;
                font-weight: 700;
                color: #E65100;
            }
            .bom-summary .stat .lbl {
                font-size: 11px;
                color: #BF360C;
                text-transform: uppercase;
            }
            .bom-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 13px;
            }
            .bom-table th {
                text-align: left;
                padding: 10px 12px;
                background: var(--control-bg);
                border-bottom: 2px solid var(--border-color);
                font-weight: 600;
                color: var(--text-muted);
                text-transform: uppercase;
                font-size: 11px;
            }
            .bom-table td {
                padding: 10px 12px;
                border-bottom: 1px solid var(--border-color);
            }
            .bom-table tr:hover {
                background: var(--control-bg);
            }
            .bom-table a {
                color: var(--primary);
                font-weight: 500;
            }
            .chart-subtitle {
                margin: -10px 0 10px 0;
                font-size: 12px;
                color: var(--text-muted);
            }
            #otd-charts-row {
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            }
        </style>
    `;

    const container = $(`
        ${styles}
        <div class="dashboard-container">
            <div class="dashboard-row" id="charts-row">
                <div class="chart-card">
                    <h3>📊 Orders by Status</h3>
                    <div class="chart-wrapper">
                        <canvas id="ordersStatusChart"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <h3>⏱️ Orders by Delay</h3>
                    <div class="chart-wrapper">
                        <canvas id="ordersDelayChart"></canvas>
                    </div>
                </div>
            </div>
            
            <!-- OTD Pie Charts Section -->
            <div class="value-cards-section">
                <h4>📈 OTD (On-Time Delivery) Analysis</h4>
            </div>
            <div class="dashboard-row" id="otd-charts-row">
                <div class="chart-card">
                    <h3>🚚 Delivery OTD</h3>
                    <p class="chart-subtitle">Actual vs Scheduled Delivery Date</p>
                    <div class="chart-wrapper">
                        <canvas id="deliveryOtdChart"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <h3>📝 Order Entry OTD</h3>
                    <p class="chart-subtitle">PO Date to SO Date (≤3 days = On Time)</p>
                    <div class="chart-wrapper">
                        <canvas id="orderEntryOtdChart"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <h3>✅ Order Approval OTD</h3>
                    <p class="chart-subtitle">SO Date to Approval (≤5 days = On Time)</p>
                    <div class="chart-wrapper">
                        <canvas id="orderApprovalOtdChart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="value-cards-section">
                <h4>📦 Order Booking Value</h4>
                <div class="value-cards-row" id="booking-cards"></div>
            </div>
            
            <div class="value-cards-section">
                <h4>🧾 Invoicing</h4>
                <div class="value-cards-row" id="invoicing-cards"></div>
            </div>
            
            <div class="value-cards-section">
                <h4>💰 Outstanding vs Collection (Current Month)</h4>
                <div class="value-cards-row" id="collection-cards"></div>
            </div>
            
            <div class="bom-section" id="bom-section">
                <h4>⚠️ BOM Release Pending > 2 Weeks</h4>
                <div id="bom-content"></div>
            </div>
        </div>
    `).appendTo(page.body);

    let statusChart = null;
    let delayChart = null;
    let deliveryOtdChart = null;
    let orderEntryOtdChart = null;
    let orderApprovalOtdChart = null;

    function load_data() {
        frappe.call({
            method: "generate_item.generate_item.page.sales_performance_da.sales_performance_da.get_dashboard_data",
            args: {
                from_date: from_date.get_value(),
                to_date: to_date.get_value(),
                branch: branch.get_value()
            },
            callback(r) {
                if (r.message) {
                    render_dashboard(r.message);
                }
            }
        });
    }

    function render_dashboard(data) {
        // Wait for Chart.js to load
        if (!window.Chart) {
            setTimeout(() => render_dashboard(data), 100);
            return;
        }

        render_orders_status_chart(data.orders_status);
        render_orders_delay_chart(data.orders_delay);
        render_booking_cards(data.order_booking);
        render_invoicing_cards(data.invoicing);
        render_collection_cards(data.outstanding_collection);
        render_bom_pending(data.bom_pending);
        
        // OTD Pie Charts
        render_delivery_otd_chart(data.delivery_otd);
        render_order_entry_otd_chart(data.order_entry_otd);
        render_order_approval_otd_chart(data.order_approval_otd);
    }

    function render_orders_status_chart(data) {
        const ctx = document.getElementById('ordersStatusChart').getContext('2d');
        
        const labels = Object.keys(data);
        const values = labels.map(k => data[k]?.value || 0);
        
        const colors = {
            'Draft': '#9E9E9E',
            'Pending Approval': '#FF9800',
            'Pending': '#FF9800',
            'Approved': '#4CAF50',
            'Booked': '#2196F3'
        };

        if (statusChart) statusChart.destroy();

        statusChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels.map(l => `${l} (${data[l]?.count || 0})`),
                datasets: [{
                    data: values,
                    backgroundColor: labels.map(l => colors[l] || '#607D8B'),
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            usePointStyle: true,
                            font: { size: 11 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw || 0;
                                return `₹ ${value.toFixed(2)} Lakh`;
                            }
                        }
                    }
                }
            }
        });
    }

    function render_orders_delay_chart(data) {
        const ctx = document.getElementById('ordersDelayChart').getContext('2d');
        
        const labels = Object.keys(data);
        const values = labels.map(k => data[k]?.value || 0);
        
        const colors = {
            'Delayed': '#F44336',
            'Not Delayed': '#4CAF50'
        };

        if (delayChart) delayChart.destroy();

        delayChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels.map(l => `${l} (${data[l]?.count || 0})`),
                datasets: [{
                    data: values,
                    backgroundColor: labels.map(l => colors[l] || '#607D8B'),
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            usePointStyle: true,
                            font: { size: 11 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw || 0;
                                return `₹ ${value.toFixed(2)} Lakh`;
                            }
                        }
                    }
                }
            }
        });
    }

    function render_booking_cards(data) {
        const html = `
            <div class="value-card fy">
                <div class="label">FY Total</div>
                <div class="value">${(data?.FY || 0).toFixed(2)} Lakh</div>
                
            </div>
            <div class="value-card month">
                <div class="label">Current Month</div>
                <div class="value">${(data?.['Current Month'] || 0).toFixed(2)} Lakh</div>
                
            </div>
        `;
        $('#booking-cards').html(html);
    }

    function render_invoicing_cards(data) {
        const html = `
            <div class="value-card fy">
                <div class="label">FY Total</div>
                <div class="value">${(data?.FY || 0).toFixed(2)} Lakh</div>
                
            </div>
            <div class="value-card month">
                <div class="label">Current Month</div>
                <div class="value">${(data?.['Current Month'] || 0).toFixed(2)} Lakh</div>
                
            </div>
        `;
        $('#invoicing-cards').html(html);
    }

    function render_collection_cards(data) {
        const html = `
            <div class="value-card outstanding">
                <div class="label">Outstanding</div>
                <div class="value">${(data?.Outstanding || 0).toFixed(2)} Lakh</div>
                
            </div>
            <div class="value-card collected">
                <div class="label">Collected</div>
                <div class="value">${(data?.Collected || 0).toFixed(2)} Lakh</div>
               
            </div>
        `;
        $('#collection-cards').html(html);
    }

    function render_bom_pending(data) {
        if (!data || !data.total) {
            $('#bom-content').html('<p class="text-muted">No pending BOM releases</p>');
            return;
        }

        const total = data.total;
        const batches = data.batches || [];

        let tableRows = '';
        if (batches.length > 0) {
            tableRows = batches.map(b => `
                <tr>
                    <td><strong>${b.batch}</strong></td>
                    <td><a href="/app/sales-order/${b.sales_order}">${b.sales_order}</a></td>
                    <td>${b.count}</td>
                    <td>₹ ${b.value.toFixed(2)} LAKH</td>
                </tr>
            `).join('');
        }

        const html = `
            <div class="bom-summary">
                <div class="stat">
                    <div class="num">${total.count}</div>
                    <div class="lbl">Items Pending</div>
                </div>
                <div class="stat">
                    <div class="num">₹ ${total.value.toFixed(2)} LAKH</div>
                    <div class="lbl">Total Value</div>
                </div>
            </div>
            ${batches.length > 0 ? `
                <table class="bom-table">
                    <thead>
                        <tr>
                            <th>Batch</th>
                            <th>Sales Order</th>
                            <th>Items</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${tableRows}
                    </tbody>
                </table>
            ` : '<p class="text-muted">No batch-wise data available</p>'}
        `;
        $('#bom-content').html(html);
    }

    // OTD Pie Chart Render Functions
    function render_delivery_otd_chart(data) {
        const ctx = document.getElementById('deliveryOtdChart').getContext('2d');
        
        const labels = Object.keys(data || {});
        const values = labels.map(k => data[k]?.value || 0);
        
        const colors = {
            'On Time': '#4CAF50',
            'Delayed': '#F44336'
        };

        if (deliveryOtdChart) deliveryOtdChart.destroy();

        deliveryOtdChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels.map(l => `${l} (${data[l]?.count || 0})`),
                datasets: [{
                    data: values,
                    backgroundColor: labels.map(l => colors[l] || '#607D8B'),
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            usePointStyle: true,
                            font: { size: 11 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw || 0;
                                return `₹ ${value.toFixed(2)} Lakh`;
                            }
                        }
                    }
                }
            }
        });
    }

    function render_order_entry_otd_chart(data) {
        const ctx = document.getElementById('orderEntryOtdChart').getContext('2d');
        
        const labels = Object.keys(data || {});
        const values = labels.map(k => data[k]?.value || 0);
        
        const colors = {
            'On Time': '#4CAF50',
            'Delayed': '#FF9800'
        };

        if (orderEntryOtdChart) orderEntryOtdChart.destroy();

        orderEntryOtdChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels.map(l => `${l} (${data[l]?.count || 0})`),
                datasets: [{
                    data: values,
                    backgroundColor: labels.map(l => colors[l] || '#607D8B'),
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            usePointStyle: true,
                            font: { size: 11 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw || 0;
                                return `₹ ${value.toFixed(2)} Lakh`;
                            }
                        }
                    }
                }
            }
        });
    }

    function render_order_approval_otd_chart(data) {
        const ctx = document.getElementById('orderApprovalOtdChart').getContext('2d');
        
        const labels = Object.keys(data || {});
        const values = labels.map(k => data[k]?.value || 0);
        
        const colors = {
            'On Time': '#4CAF50',
            'Delayed': '#9C27B0'
        };

        if (orderApprovalOtdChart) orderApprovalOtdChart.destroy();

        orderApprovalOtdChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels.map(l => `${l} (${data[l]?.count || 0})`),
                datasets: [{
                    data: values,
                    backgroundColor: labels.map(l => colors[l] || '#607D8B'),
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            usePointStyle: true,
                            font: { size: 11 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw || 0;
                                return `₹ ${value.toFixed(2)} Lakh`;
                            }
                        }
                    }
                }
            }
        });
    }

    // Initial load with small delay for Chart.js
    setTimeout(load_data, 200);
};
