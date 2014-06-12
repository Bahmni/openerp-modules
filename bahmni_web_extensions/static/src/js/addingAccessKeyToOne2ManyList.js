openerp.bahmni_web_extensions.addingAccessKeyToOne2ManyList = function(instance) {
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;
    instance.web.form.One2ManyList.include({
        pad_table_to: function () {
            this._super.apply(this, arguments);

            var add_item_link = this.$current.find("td.oe_form_field_one2many_list_row_add a");
            add_item_link.attr("accesskey", "I");
            add_item_link.html("<span>Add an </span><span class='accesskey-char'>I</span><span>tem</span>");
        }
    });

    instance.web.ListView.Groups.include({
        render_groups: function (datagroups) {
            var self = this;
            var placeholder = this.make_fragment();
            _(datagroups).each(function (group, index) {
                if (self.children[group.value]) {
                    self.records.proxy(group.value).reset();
                    delete self.children[group.value];
                }
                var child = self.children[group.value] = new (self.view.options.GroupsType)(self.view, {
                    records: self.records.proxy(group.value),
                    options: self.options,
                    columns: self.columns
                });
                self.bind_child_events(child);
                child.datagroup = group;

                var $row = child.$row = $('<tr class="oe_group_header">');
                if (group.openable && group.length) {
                    $row.click(function (e) {
                        if (!$row.data('open')) {
                            $row.data('open', true)
                                .find('span.ui-icon')
                                    .removeClass('ui-icon-triangle-1-e')
                                    .addClass('ui-icon-triangle-1-s');
                            child.open(self.point_insertion(e.currentTarget));
                        } else {
                            $row.removeData('open')
                                .find('span.ui-icon')
                                    .removeClass('ui-icon-triangle-1-s')
                                    .addClass('ui-icon-triangle-1-e');
                            child.close();
                        }
                    });
                }
                placeholder.appendChild($row[0]);
                // BAHMNI CHANGE_START
                var $line_number_column = $('<td>').appendTo($row);
                $line_number_column.html(index + 1);
                // BAHMNI CHANGE_END

                var $group_column = $('<th class="oe_list_group_name">').appendTo($row);
                // Don't fill this if group_by_no_leaf but no group_by
                if (group.grouped_on) {
                    var row_data = {};
                    row_data[group.grouped_on] = group;
                    var group_column = _(self.columns).detect(function (column) {
                        return column.id === group.grouped_on; });
                    if (! group_column) {
                        throw new Error(_.str.sprintf(
                            _t("Grouping on field '%s' is not possible because that field does not appear in the list view."),
                            group.grouped_on));
                    }
                    var group_label;
                    try {
                        group_label = group_column.format(row_data, {
                            value_if_empty: _t("Undefined"),
                            process_modifiers: false
                        });
                    } catch (e) {
                        group_label = _.str.escapeHTML(row_data[group_column.id].value);
                    }
                    // group_label is html-clean (through format or explicit
                    // escaping if format failed), can inject straight into HTML
                    $group_column.html(_.str.sprintf(_t("%s (%d)"),
                        group_label, group.length));

                    if (group.length && group.openable) {
                        // Make openable if not terminal group & group_by_no_leaf
                        $group_column.prepend('<span class="ui-icon ui-icon-triangle-1-e" style="float: left;">');
                    } else {
                        // Kinda-ugly hack: jquery-ui has no "empty" icon, so set
                        // wonky background position to ensure nothing is displayed
                        // there but the rest of the behavior is ui-icon's
                        $group_column.prepend('<span class="ui-icon" style="float: left; background-position: 150px 150px">');
                    }
                }
                self.indent($group_column, group.level);

                if (self.options.selectable) {
                    $row.append('<td>');
                }
                _(self.columns).chain()
                    .filter(function (column) { return column.invisible !== '1'; })
                    .each(function (column) {
                        if (column.meta) {
                            // do not do anything
                        } else if (column.id in group.aggregates) {
                            var r = {};
                            r[column.id] = {value: group.aggregates[column.id]};
                            $('<td class="oe_number">')
                                .html(column.format(r, {process_modifiers: false}))
                                .appendTo($row);
                        } else {
                            $row.append('<td>');
                        }
                    });
                if (self.options.deletable) {
                    $row.append('<td class="oe_list_group_pagination">');
                }
            });
            return placeholder;
        },

    });
}