/**
 * SaaS Form Layout Fix
 * Ensures chatter stays below sheet on all screen sizes for SaaS forms
 */
odoo.define('onedesk_core.saas_form_layout', function (require) {
    'use strict';

    var FormController = require('web.FormController');

    FormController.include({
        /**
         * Override to fix chatter layout for SaaS forms
         */
        _onLoadRecord: function () {
            var res = this._super.apply(this, arguments);

            // Check if this is a SaaS form
            if (['saas.client', 'saas.plan', 'saas.database', 'saas.alert'].indexOf(this.modelName) !== -1) {
                this._fixSaasFormLayout();
            }

            return res;
        },

        /**
         * Fix the layout by moving chatter to end of form container
         */
        _fixSaasFormLayout: function () {
            var self = this;

            // Wait for DOM to be ready
            setTimeout(function () {
                var $form = self.$('.o_form_view');
                if (!$form.length) {
                    return;
                }

                var $sheetBg = $form.find('.o_form_sheet_bg');
                var $chatter = $form.find('.o_chatter_bottom, .oe_chatter');

                if (!$sheetBg.length || !$chatter.length) {
                    return;
                }

                // Ensure form is flex column
                $form.css({
                    'display': 'flex',
                    'flex-direction': 'column',
                    'width': '100%'
                });

                // Ensure sheet_bg is flex column
                $sheetBg.css({
                    'display': 'flex',
                    'flex-direction': 'column',
                    'width': '100%',
                    'flex': 'none'
                });

                // Ensure chatter is at bottom
                $chatter.css({
                    'display': 'block',
                    'width': '100%',
                    'flex': 'none',
                    'clear': 'both',
                    'margin-top': '30px',
                    'margin-left': '0',
                    'order': '2'
                });

                // Set order for sheet
                $sheetBg.css('order', '1');

            }, 100);
        }
    });

    return FormController;
});
