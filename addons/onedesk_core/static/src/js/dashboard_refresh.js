odoo.define('onedesk_core.dashboard_refresh', function(require) {
    'use strict';

    const rpc = require('web.rpc');
    const Widget = require('web.Widget');

    /**
     * OneDesk Dashboard Auto-Refresh Module
     * Handles real-time updates of dashboard metrics
     */

    const DashboardRefresh = Widget.extend({
        init: function() {
            this._super.apply(this, arguments);
            this.refreshInterval = 300000; // 5 minutes default
            this.autoRefreshEnabled = false;
            this.refreshTimer = null;
            this.lastUpdateTime = null;
        },

        /**
         * Initialize dashboard refresh listener
         */
        start: function() {
            this._super.apply(this, arguments);
            this._setupDashboardRefresh();
            return Promise.resolve();
        },

        /**
         * Setup dashboard refresh on page load
         */
        _setupDashboardRefresh: function() {
            // Check if we're on the dashboard page
            const isDashboardPage = this._isDashboardPage();
            if (!isDashboardPage) {
                return;
            }

            // Load dashboard configuration from server
            rpc.query({
                route: '/onedesk/dashboard/config',
                params: {},
            }).then((config) => {
                this.autoRefreshEnabled = config.auto_refresh;
                this.refreshInterval = config.refresh_interval * 1000; // Convert to milliseconds

                if (this.autoRefreshEnabled) {
                    this._startAutoRefresh();
                    this._updateLastRefreshTime();
                }
            }).catch((error) => {
                console.error('Error loading dashboard config:', error);
            });
        },

        /**
         * Check if current page is dashboard
         */
        _isDashboardPage: function() {
            const currentController = window.location.pathname;
            return currentController.includes('dashboard') ||
                   currentController.includes('onedesk');
        },

        /**
         * Start auto-refresh timer
         */
        _startAutoRefresh: function() {
            if (this.refreshTimer) {
                clearInterval(this.refreshTimer);
            }

            this.refreshTimer = setInterval(() => {
                this._refreshDashboardData();
            }, this.refreshInterval);

            // Initial refresh
            this._refreshDashboardData();
        },

        /**
         * Stop auto-refresh timer
         */
        _stopAutoRefresh: function() {
            if (this.refreshTimer) {
                clearInterval(this.refreshTimer);
                this.refreshTimer = null;
            }
        },

        /**
         * Refresh all dashboard metrics
         */
        _refreshDashboardData: function() {
            rpc.query({
                route: '/onedesk/dashboard/data',
                params: {},
            }).then((response) => {
                if (response.status === 'success') {
                    this._updateDashboardUI(response.data);
                    this._updateLastRefreshTime();
                }
            }).catch((error) => {
                console.error('Error refreshing dashboard:', error);
            });
        },

        /**
         * Refresh specific metric group
         */
        _refreshSpecificMetric: function(metricType) {
            rpc.query({
                route: `/onedesk/dashboard/metrics/${metricType}`,
                params: {},
            }).then((response) => {
                if (response.status === 'success') {
                    this._updateMetricInUI(metricType, response.data);
                }
            }).catch((error) => {
                console.error(`Error refreshing ${metricType} metrics:`, error);
            });
        },

        /**
         * Update dashboard UI with new data
         */
        _updateDashboardUI: function(data) {
            // Update properties metrics
            this._updateMetric('properties', data.properties);

            // Update units metrics
            this._updateMetric('units', data.units);

            // Update reservations metrics
            this._updateMetric('reservations', data.reservations);

            // Update tasks metrics
            this._updateMetric('tasks', data.tasks);

            // Update financial metrics
            this._updateMetric('financial', data.financial);
        },

        /**
         * Update specific metric group in UI
         */
        _updateMetric: function(metricType, metricData) {
            // Find all elements with data-metric-type attribute
            const elements = document.querySelectorAll(`[data-metric-type="${metricType}"]`);

            elements.forEach((element) => {
                const metricName = element.getAttribute('data-metric-name');
                if (metricName && metricData[metricName] !== undefined) {
                    const value = metricData[metricName];

                    // Format value if needed
                    const formattedValue = this._formatMetricValue(metricType, metricName, value);

                    // Update element with animation
                    this._animateUpdate(element, formattedValue);
                }
            });
        },

        /**
         * Update single metric in UI
         */
        _updateMetricInUI: function(metricType, metricData) {
            this._updateMetric(metricType, metricData);
        },

        /**
         * Format metric value based on type
         */
        _formatMetricValue: function(metricType, metricName, value) {
            // Format currency values
            if (metricName.includes('revenue') || metricName.includes('payment') || metricName.includes('outstanding')) {
                return this._formatCurrency(value);
            }

            // Format percentage values
            if (metricName.includes('rate')) {
                return value.toFixed(1) + '%';
            }

            // Default: return as is
            return value;
        },

        /**
         * Format number as currency
         */
        _formatCurrency: function(value) {
            return new Intl.NumberFormat('fr-FR', {
                style: 'currency',
                currency: 'EUR'
            }).format(value);
        },

        /**
         * Animate element update
         */
        _animateUpdate: function(element, newValue) {
            // Add fade effect
            element.style.opacity = '0.5';
            element.textContent = newValue;

            setTimeout(() => {
                element.style.opacity = '1';
            }, 100);
        },

        /**
         * Update last refresh time display
         */
        _updateLastRefreshTime: function() {
            this.lastUpdateTime = new Date();
            const timeElement = document.querySelector('.dashboard-update-time');

            if (timeElement) {
                const timeString = this.lastUpdateTime.toLocaleTimeString('fr-FR');
                timeElement.textContent = timeString;
            }
        },

        /**
         * Cleanup on destroy
         */
        destroy: function() {
            this._stopAutoRefresh();
            this._super.apply(this, arguments);
        },
    });

    // Auto-start dashboard refresh when page loads
    $(document).ready(function() {
        if ($('[data-dashboard="true"]').length > 0) {
            new DashboardRefresh().attachTo($('body'));
        }
    });

    return DashboardRefresh;
});
