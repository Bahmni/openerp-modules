
openerp.bahmni_customer_payment = function (instance) {
    {
        var _t = instance.web._t,
            _lt = instance.web._lt;
        var QWeb = instance.web.qweb;
        instance.bahmni_customer_payment = {};

        instance.bahmni_customer_payment.validatePay = instance.web.form.FieldFloat.extend({
                is_field_number: true,
            widget_class: 'oe_form_field_float',
            init: function (field_manager, node) {
                    this._super(field_manager, node);
                    this.internal_set_value(0.0);
                    if (this.node.attrs.digits) {
                        this.digits = this.node.attrs.digits;
                    } else {
                        this.digits = this.field.digits;
                    }
                },
                set_value: function(value_) {
                    if(value_ == -999999){
                        value_ = '';
                    }
                    if (value_ === false || value_ === undefined) {
                        // As in GTK client, floats default to 0
                        value_ = 0.0;
                    }
                this._super.apply(this, [value_]);
            },
            focus: function() {
                this.$('input:first').select();
            }
        });

        instance.web.form.widgets.add('validatePay', 'instance.bahmni_customer_payment.validatePay');
    }

}