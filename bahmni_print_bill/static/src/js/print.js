openerp.bahmni_print_bill = function(instance) {

    var QWeb = instance.web.qweb;
    instance.bahmni_print_bill.print = instance.web.form.FieldChar.extend({
        template: "print_button",
        init: function(parent, action) {
            this._super.apply(this, arguments);
            this._start = null;
            this.parent = parent;
       },

       start: function() {
            this._super.apply(this, arguments);
            $('button#print-bill-button').click($.proxy(function() {
                $('button#print-bill-button').attr("disabled", true);
                var self = this;
                this.fetchAndPrintBill("Bill", function(bill) {
                    setTimeout(function() {self.gotoQuotation()}, 700);
                    $('button#print-bill-button').attr("disabled", false);
                });
            }, this));

            $('button#print-summary-bill-button').click($.proxy(function() {
                $('button#print-summary-bill-button').attr("disabled", true);
                var self = this;
                this.fetchAndPrintBill("BillSummary", function(bill) {
                    setTimeout(function() {self.gotoQuotation()}, 700);
                    $('button#print-summary-bill-button').attr("disabled", false);
                });
            }, this));

            $('button#print-bill-latest-prescription').click($.proxy(function() {
                $('button#print-bill-latest-prescription').attr("disabled", true);
                var self = this;
                this.fetchAndPrintBill("Bill", function(bill) {
                    self.printLatestPrescription(bill);
                    $('button#print-bill-latest-prescription').attr("disabled", false);
                });
            }, this));
        },

        fetch: function() {
            return this.rpc('/invoice/bill', {voucher_id: this.parent.datarecord.id});
        },

        fetchAndPrintBill: function(billTemplate, callBack) {
            var self = this;
            this.fetch().done(function(bill) {
                self.transform(bill);
                self.printReceipt(bill, billTemplate);
                if(callBack != undefined) {
                    callBack(bill);
                }
            });
        },

        printReceipt: function(bill, billTemplate) {
            var $ht = $(QWeb.render(billTemplate, bill))[0];
            var hiddenFrame = $("#printBillFrame")[0];
            var doc = hiddenFrame.contentWindow.document.open("text/html", "replace");
            doc.write($ht.innerHTML);
            doc.close();
            setTimeout(function() {
                hiddenFrame.contentWindow.print();
            }, 500);
        },

        printLatestPrescription: function(bill) {
            window.open("https://" + window.location.hostname + "/bahmni/clinical/#/default/patient/" + bill.partner_uuid + "/latest-prescription-print");
        },

        gotoQuotation: function() {
            window.location = "/?ts=1370260915528#page=0&limit=80&view_type=list&model=account.voucher&menu_id=291&action=357";
        },

        transform: function(bill) {
            bill.voucher_date = $.datepicker.formatDate('dd/mm/yy', new Date(bill.voucher_date));
            bill.amount_tax = bill.amount_tax.toFixed(2);
            bill.new_charges = bill.new_charges.toFixed(2);
            bill.discount = bill.discount.toFixed(2);
            bill.net_amount = bill.net_amount.toFixed(2);
            bill.previous_balance = bill.previous_balance.toFixed(2);
            bill.bill_amount = bill.bill_amount.toFixed(2);
            bill.paid_amount = bill.paid_amount.toFixed(2);
            bill.balance_amount = bill.balance_amount.toFixed(2);

            bill.invoice_line_items.forEach(function(invoice_line_item) {
                invoice_line_item.unit_price = invoice_line_item.unit_price.toFixed(2);
                invoice_line_item.quantity = invoice_line_item.quantity.toFixed(3);
                invoice_line_item.subtotal = invoice_line_item.subtotal.toFixed(2);
            });

            this.summarize(bill);
        },

        summarize: function(bill) {
            bill.categories = Object.keys(_.groupBy(bill.invoice_line_items, function(item) {
                return item.product_category;
            })).join(", ");
        }
    });

    instance.web.form.widgets.add('print-bill', 'instance.bahmni_print_bill.print');
}
