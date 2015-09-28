openerp.bahmni_sale_discount = function(instance) {

    var QWeb = instance.web.qweb;
    instance.bahmni_sale_discount.linkPrescription = instance.web.form.FieldChar.extend({
        template: "link_prescription",
        init: function(parent, action) {
            this._super.apply(this, arguments);
            this._start = null;
            this.parent = parent;
       },

       start: function() {
            this._super.apply(this, arguments);
            $('button#latest-prescription').click($.proxy(function() {
                if(this.parent.datarecord.partner_uuid != null) {
                    this.openLatestPrescription(this.parent.datarecord.partner_uuid);
                } else {
                    alert("This patient does not have a proper ID to show latest prescription. Please use clinical app.");
                }
            }, this));
        },

        openLatestPrescription: function(partner_uuid) {
            window.open("https://" + window.location.hostname + "/bahmni/clinical/#/default/patient/" + partner_uuid + "/treatment");
        },
    });

    instance.web.form.widgets.add('link-prescription', 'instance.bahmni_sale_discount.linkPrescription');
}
