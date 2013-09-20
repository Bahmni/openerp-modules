openerp.bahmni_web_extensions.accesskeyHighlight = function(instance) {
    instance.web.ViewManager.include({
        start: function() {
            this._super.apply(this, arguments);
            var createUnderlinedAccessKeyElem = function(text, accesskey) {
                if(text == null) {
                    return null;
                } else if(accesskey == null || accesskey == "") {
                    return text;
                }
                var i = text.toLowerCase().indexOf(accesskey.toLowerCase());
                return "<span>" + text.slice(0, i) + "</span><span class='accesskey-char'>" + accesskey + "</span><span>" + text.slice(i+1) + "</span>";
            };

            $("[accesskey]").each(function(index, elem) {
                var newInnerHtml = createUnderlinedAccessKeyElem(elem.innerText, elem.accessKey);
                if(newInnerHtml != null) {
                    elem.innerHTML = newInnerHtml;
                }
            });
        },

    });

    instance.web.form.FormRenderingEngine.include({
        process_label: function($label) {
            var name = $label.attr("for"),
                field_orm = this.fvg.fields[name];
            var dict = {
                string: $label.attr('string') || (field_orm || {}).string || '',
                help: $label.attr('help') || (field_orm || {}).help || '',
                _for: name ? _.uniqueId('oe-field-input-') : undefined,
                accesskey: $label.attr('accesskey'),
            };
            var align = parseFloat(dict.align);
            if (isNaN(align) || align === 1) {
                align = 'right';
            } else if (align === 0) {
                align = 'left';
            } else {
                align = 'center';
            }
            dict.align = align;
            var $new_label = this.render_element('FormRenderingLabel', dict);
            $label.before($new_label).remove();
            this.handle_common_properties($new_label, $label);
            if (name) {
                this.labels[name] = $new_label;
            }
            return $new_label;
        },

        preprocess_field: function($field) {
            var self = this;
            var name = $field.attr('name'),
                field_colspan = parseInt($field.attr('colspan'), 10),
                field_modifiers = JSON.parse($field.attr('modifiers') || '{}');

            if ($field.attr('nolabel') === '1')
                return;
            $field.attr('nolabel', '1');
            var found = false;
            this.$form.find('label[for="' + name + '"]').each(function(i ,el) {
                $(el).parents().each(function(unused, tag) {
                    var name = tag.tagName.toLowerCase();
                    if (name === "field" || name in self.tags_registry.map)
                        found = true;
                });
            });
            if (found)
                return;

            var $label = $('<label/>').attr({
                'for' : name,
                "modifiers": JSON.stringify({invisible: field_modifiers.invisible}),
                "string": $field.attr('string'),
                "help": $field.attr('help'),
                "class": $field.attr('class'),
                "accesskey": $field.attr('accesskey'),
            });
            $label.insertBefore($field);
            if (field_colspan > 1) {
                $field.attr('colspan', field_colspan - 1);
            }
            return $label;
        },

    });
};
