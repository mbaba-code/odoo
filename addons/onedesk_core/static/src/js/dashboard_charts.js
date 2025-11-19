odoo.define('onedesk_core.dashboard_charts', function(require) {
    'use strict';

    const rpc = require('web.rpc');
    const Widget = require('web.Widget');

    /**
     * Dashboard Charts Widget
     * Displays revenue, occupancy, and reservation charts
     */
    const DashboardCharts = Widget.extend({
        init: function() {
            this._super.apply(this, arguments);
            this.charts = {};
        },

        start: function() {
            this._super.apply(this, arguments);
            this._loadCharts();
            return Promise.resolve();
        },

        _loadCharts: function() {
            const self = this;

            // Check if on dashboard page
            const dashboardForm = this.$('[data-oemodel="onedesk.dashboard"]');
            if (dashboardForm.length === 0) {
                return;
            }

            // Load revenue chart
            this._loadRevenueChart();

            // Load occupancy chart
            this._loadOccupancyChart();

            // Load reservations chart
            this._loadReservationsChart();
        },

        _loadRevenueChart: function() {
            const self = this;

            rpc.query({
                route: '/onedesk/dashboard/revenue-chart',
                params: {},
            }).then(function(response) {
                if (response.status === 'success') {
                    self._renderChart('revenue-chart-container', {
                        type: 'line',
                        title: 'Revenue Trend',
                        labels: response.labels,
                        data: response.data,
                        borderColor: '#ff9800',
                        backgroundColor: 'rgba(255, 152, 0, 0.1)'
                    });
                }
            }).catch(function(error) {
                console.error('Error loading revenue chart:', error);
            });
        },

        _loadOccupancyChart: function() {
            const self = this;

            rpc.query({
                route: '/onedesk/dashboard/occupancy-chart',
                params: {},
            }).then(function(response) {
                if (response.status === 'success') {
                    self._renderChart('occupancy-chart-container', {
                        type: 'bar',
                        title: 'Property Occupancy Rates',
                        labels: response.labels,
                        data: response.data,
                        borderColor: '#17a2b8',
                        backgroundColor: 'rgba(23, 162, 184, 0.7)'
                    });
                }
            }).catch(function(error) {
                console.error('Error loading occupancy chart:', error);
            });
        },

        _loadReservationsChart: function() {
            const self = this;

            rpc.query({
                route: '/onedesk/dashboard/reservations-chart',
                params: {},
            }).then(function(response) {
                if (response.status === 'success') {
                    const colors = [
                        'rgba(108, 117, 125, 0.7)',  // gray
                        'rgba(40, 167, 69, 0.7)',    // green
                        'rgba(23, 162, 184, 0.7)',   // cyan
                        'rgba(28, 123, 171, 0.7)',   // blue
                        'rgba(220, 53, 69, 0.7)'     // red
                    ];

                    self._renderChart('reservations-chart-container', {
                        type: 'doughnut',
                        title: 'Reservations by Status',
                        labels: response.labels,
                        data: response.data,
                        backgroundColors: colors
                    });
                }
            }).catch(function(error) {
                console.error('Error loading reservations chart:', error);
            });
        },

        _renderChart: function(containerId, config) {
            const container = document.getElementById(containerId);
            if (!container) {
                return;
            }

            // Check if Chart.js is available
            if (typeof Chart === 'undefined') {
                container.innerHTML = '<p style="color: #999;">Chart library not loaded</p>';
                return;
            }

            // Create canvas if not exists
            let canvas = container.querySelector('canvas');
            if (!canvas) {
                canvas = document.createElement('canvas');
                container.appendChild(canvas);
            }

            // Destroy existing chart if any
            if (this.charts[containerId]) {
                this.charts[containerId].destroy();
            }

            // Determine colors
            let backgroundColor, borderColor;
            if (config.type === 'doughnut') {
                backgroundColor = config.backgroundColors;
                borderColor = '#fff';
            } else {
                backgroundColor = config.backgroundColor;
                borderColor = config.borderColor;
            }

            // Create new chart
            this.charts[containerId] = new Chart(canvas, {
                type: config.type,
                data: {
                    labels: config.labels,
                    datasets: [{
                        label: config.title,
                        data: config.data,
                        backgroundColor: backgroundColor,
                        borderColor: borderColor,
                        borderWidth: config.type === 'doughnut' ? 2 : 1,
                        tension: config.type === 'line' ? 0.3 : undefined,
                        fill: config.type === 'line',
                        pointRadius: config.type === 'line' ? 4 : undefined,
                        pointBackgroundColor: borderColor,
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            display: config.type === 'doughnut',
                            position: 'bottom'
                        },
                        title: {
                            display: true,
                            text: config.title,
                            font: {
                                size: 14,
                                weight: 'bold'
                            }
                        }
                    },
                    scales: config.type === 'doughnut' ? {} : {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    if (config.title.includes('Revenue')) {
                                        return '€' + value.toLocaleString();
                                    } else if (config.title.includes('Occupancy')) {
                                        return value + '%';
                                    }
                                    return value;
                                }
                            }
                        }
                    }
                }
            });
        },

        destroy: function() {
            // Destroy all charts
            for (let chartId in this.charts) {
                if (this.charts[chartId]) {
                    this.charts[chartId].destroy();
                }
            }
            this._super.apply(this, arguments);
        }
    });

    // Auto-initialize when page loads
    $(document).ready(function() {
        if ($('[data-oemodel="onedesk.dashboard"]').length > 0) {
            new DashboardCharts().attachTo($('body'));
        }
    });

    return DashboardCharts;
});
