/**
 * Document Form Layout Fix
 * Ensures chatter stays below sheet on all screen sizes
 */
odoo.define('onedesk_core.document_form_layout', function (require) {
    'use strict';

    var FormController = require('web.FormController');

    FormController.include({
        /**
         * Override to fix chatter layout for document forms
         */
        _onLoadRecord: function () {
            var res = this._super.apply(this, arguments);

            // Check if this is a document form
            if (this.modelName === 'onedesk.document') {
                this._fixDocumentFormLayout();
            }

            return res;
        },

        /**
         * Fix the layout by moving chatter to end of form container
         */
        _fixDocumentFormLayout: function () {
            var self = this;

            // Wait for DOM to be ready
            setTimeout(function () {
                var $form = self.$('.o_form_document_wrapper');
                if (!$form.length) {
                    return;
                }

                var $sheetBg = $form.find('.o_form_sheet_bg');
                var $chatter = $form.find('.o_chatter_bottom');

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
