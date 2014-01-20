openerp.bahmni_web_extensions = function(session) {
    var files = ["fixingErrorInCancelEdition", "addingAccessKeyToOne2ManyList", 
    "accesskeyHighlight", "addSerialNumberToListView", "addContextOnExport"];
    for(var i=0; i<files.length; i++) {
        if(openerp.bahmni_web_extensions[files[i]]) {
            openerp.bahmni_web_extensions[files[i]](session);
        }
    }
};
