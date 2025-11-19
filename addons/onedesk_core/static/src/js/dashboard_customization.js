odoo.define('onedesk_core.dashboard_customization', function(require) {
    'use strict';

    const Widget = require('web.Widget');

    /**
     * Dashboard Customization Module
     * Handles drag & drop, widget reordering, and configuration persistence
     */
    const DashboardCustomization = Widget.extend({
        init: function() {
            this._super.apply(this, arguments);
            this.widgetPositions = {};
        },

        start: function() {
            this._super.apply(this, arguments);
            this._initDragAndDrop();
            this._loadCustomization();
            return Promise.resolve();
        },

        _initDragAndDrop: function() {
            const self = this;
            const sections = document.querySelectorAll('.dashboard-section');

            if (sections.length === 0) {
                return;
            }

            sections.forEach((section) => {
                // Make sections draggable
                section.draggable = true;
                section.style.cursor = 'move';

                // Drag events
                section.addEventListener('dragstart', function(e) {
                    self._onDragStart(e);
                });

                section.addEventListener('dragover', function(e) {
                    self._onDragOver(e);
                });

                section.addEventListener('drop', function(e) {
                    self._onDrop(e);
                });

                section.addEventListener('dragend', function(e) {
                    self._onDragEnd(e);
                });
            });
        },

        _onDragStart: function(e) {
            e.target.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/html', e.target.innerHTML);
        },

        _onDragOver: function(e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';

            const target = e.target.closest('.dashboard-section');
            if (target && e.target !== target) {
                target.style.opacity = '0.5';
            }
        },

        _onDrop: function(e) {
            e.preventDefault();
            const target = e.target.closest('.dashboard-section');
            const dragging = document.querySelector('.dragging');

            if (target && target !== dragging) {
                // Swap positions
                const temp = dragging.outerHTML;
                dragging.outerHTML = target.outerHTML;
                target.outerHTML = temp;

                // Reinitialize drag and drop after swapping
                this._initDragAndDrop();

                // Save customization
                this._saveCustomization();
            }
        },

        _onDragEnd: function(e) {
            e.target.classList.remove('dragging');

            // Reset opacity
            document.querySelectorAll('.dashboard-section').forEach((section) => {
                section.style.opacity = '1';
            });
        },

        _saveCustomization: function() {
            const sections = document.querySelectorAll('.dashboard-section');
            const order = [];

            sections.forEach((section, index) => {
                const title = section.querySelector('.section-title');
                if (title) {
                    order.push({
                        index: index,
                        title: title.textContent
                    });
                }
            });

            // Save to localStorage
            localStorage.setItem('dashboard_customization', JSON.stringify({
                sections_order: order,
                saved_at: new Date().toISOString()
            }));
        },

        _loadCustomization: function() {
            const saved = localStorage.getItem('dashboard_customization');
            if (!saved) {
                return;
            }

            try {
                const customization = JSON.parse(saved);
                // Apply saved customization if needed
                console.log('Dashboard customization loaded:', customization);
            } catch (e) {
                console.error('Error loading dashboard customization:', e);
            }
        }
    });

    // Auto-initialize on dashboard page
    $(document).ready(function() {
        if ($('[data-oemodel="onedesk.dashboard"]').length > 0) {
            new DashboardCustomization().attachTo($('body'));
        }
    });

    return DashboardCustomization;
});
