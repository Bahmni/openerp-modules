OPENERP_ROOT=`cat $1.properties | grep openerp_deploy_root | cut -f2 -d"="`
cp -r ../product_pharmacy/ $OPENERP_ROOT