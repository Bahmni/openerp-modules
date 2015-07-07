\set start_date '2015-01-01';
\set end_date '2015-12-31';

-- Number of patient
SELECT 
    CASE WHEN care_setting is not NULL THEN care_setting
         ELSE 'N/A'
    END,
    count(distinct partner_id) as "Number of patient"
FROM sale_order
WHERE
    date_order >= :'start_date' and date_order <= :'end_date'
    AND sale_order.state != 'cancel'
GROUP BY care_setting
ORDER BY care_setting;



-- Number of bills raised
SELECT 
    CASE WHEN care_setting is not NULL THEN care_setting
         ELSE 'N/A'
    END,
    count(*) as "Number of Bill Raised"
FROM sale_order
WHERE
    date_order >= :'start_date' and date_order <= :'end_date'
    AND sale_order.state != 'cancel'
GROUP BY care_setting
ORDER BY care_setting;

-- Total Bill amount
SELECT 
    CASE WHEN care_setting is not NULL THEN care_setting
         ELSE 'N/A'
    END,
    sum(amount_total) as "Total Bill Amount"
FROM sale_order
WHERE
    date_order >= :'start_date' and date_order <= :'end_date'
    AND sale_order.state != 'cancel'
GROUP BY care_setting
ORDER BY care_setting;


-- Total paid amount
SELECT 
    CASE WHEN care_setting is not NULL THEN care_setting
         ELSE 'N/A'
    END,
    sum(account_voucher_line.amount) as "Total Paid Amount"
FROM account_voucher_line
INNER JOIN account_voucher on account_voucher_line.voucher_id = account_voucher.id
INNER JOIN account_move_line on account_voucher_line.move_line_id = account_move_line.id
INNER JOIN sale_order on sale_order.name = account_move_line.ref
WHERE
    date_order >= :'start_date' and date_order <= :'end_date'
    AND sale_order.state != 'cancel'
    AND account_voucher.state != 'cancel'
GROUP BY care_setting
ORDER BY care_setting;


-- Total Discount amount
SELECT 
    CASE WHEN care_setting is not NULL THEN care_setting
         ELSE 'N/A'
    END,
    sum(discount) as "Total Discount Amount"
FROM sale_order
WHERE
    date_order >= :'start_date' and date_order <= :'end_date'
    AND sale_order.state != 'cancel'
GROUP BY care_setting
ORDER BY care_setting;


-- Total Credit amount
SELECT
    CASE WHEN care_setting is not NULL THEN care_setting
         ELSE 'N/A'
    END,
    sum(amount_original - total_paid) as "Total Credit amount"
FROM
    (Select 
        account_voucher_line.name, move_line_id, amount_original, sum(account_voucher_line.amount) as total_paid, bool_or(reconcile) as reconciled
    from account_voucher_line
    INNER JOIN account_voucher on account_voucher_line.voucher_id = account_voucher.id
    WHERE account_voucher.state != 'cancel'
    group by account_voucher_line.name, move_line_id, amount_original
    ) bill_payment
INNER JOIN account_move_line on bill_payment.move_line_id = account_move_line.id
INNER JOIN sale_order on sale_order.name = account_move_line.ref
WHERE
    bill_payment.reconciled = false
    AND date_order >= :'start_date' and date_order <= :'end_date'
    AND sale_order.state != 'cancel'
GROUP BY care_setting
ORDER BY care_setting;


-- Mean bill amount
SELECT 
    CASE WHEN care_setting is not NULL THEN care_setting
         ELSE 'N/A'
    END,
    sum(amount_total)/count(*) as "Mean Bill amount"
FROM sale_order
WHERE
    date_order >= :'start_date' and date_order <= :'end_date'
    AND sale_order.state != 'cancel'
GROUP BY care_setting
ORDER BY care_setting;


-- Mean paid amount
SELECT
    CASE WHEN care_setting is not NULL THEN care_setting
         ELSE 'N/A'
    END,
    sum(total_paid) / count(sale_order.id) as "Mean Paid amount"
FROM
    (Select 
        account_voucher_line.name, move_line_id, amount_original, sum(account_voucher_line.amount) as total_paid, bool_or(reconcile) as reconciled
    from account_voucher_line
    INNER JOIN account_voucher on account_voucher_line.voucher_id = account_voucher.id
    WHERE account_voucher.state != 'cancel'
    group by account_voucher_line.name, move_line_id, amount_original
    ) bill_payment
INNER JOIN account_move_line on bill_payment.move_line_id = account_move_line.id
INNER JOIN sale_order on sale_order.name = account_move_line.ref
WHERE
    date_order >= :'start_date' and date_order <= :'end_date'
    AND sale_order.state != 'cancel'
GROUP BY care_setting
ORDER BY care_setting;


-- Mean discount amount
SELECT 
    CASE WHEN care_setting is not NULL THEN care_setting
         ELSE 'N/A'
    END,
    sum(discount)/count(*) as "Mean Discount Amount"
FROM sale_order
WHERE
    discount != 0.0
    AND date_order >= :'start_date' and date_order <= :'end_date'
    AND sale_order.state != 'cancel'
GROUP BY care_setting
ORDER BY care_setting;


-- Mean credit amount
Select 
    CASE WHEN care_setting is not NULL THEN care_setting
         ELSE 'N/A'
    END,
    sum(amount_original - total_paid) / count(sale_order.id) as "Mean Credit Amount"
FROM
    (Select 
        account_voucher_line.name, move_line_id, amount_original, sum(account_voucher_line.amount) as total_paid, bool_or(reconcile) as reconciled
    from account_voucher_line
    INNER JOIN account_voucher on account_voucher_line.voucher_id = account_voucher.id
    WHERE account_voucher.state != 'cancel'
    group by account_voucher_line.name, move_line_id, amount_original
    order by name
    ) bill_payment
INNER JOIN account_move_line on bill_payment.move_line_id = account_move_line.id
INNER JOIN sale_order on sale_order.name = account_move_line.ref
WHERE
    bill_payment.reconciled = false
    AND date_order >= :'start_date' and date_order <= :'end_date'
    AND sale_order.state != 'cancel'
GROUP BY care_setting
ORDER BY care_setting;



-- % of bills paid 100%
Select
    CASE WHEN care_setting is not NULL THEN care_setting
         ELSE 'N/A'
    END,
    count(sale_order.id) as "Number of bill paid 100%"
FROM
    (Select 
        account_voucher_line.name, move_line_id, amount_original, sum(account_voucher_line.amount) as total_paid, bool_or(reconcile) as reconciled
    from account_voucher_line
    INNER JOIN account_voucher on account_voucher_line.voucher_id = account_voucher.id
    WHERE account_voucher.state != 'cancel'
    group by account_voucher_line.name, move_line_id, amount_original
    order by name
    ) bill_payment
INNER JOIN account_move_line on bill_payment.move_line_id = account_move_line.id
INNER JOIN sale_order on sale_order.name = account_move_line.ref
WHERE
    bill_payment.reconciled = true
    AND date_order >= :'start_date' and date_order <= :'end_date'
    AND sale_order.state != 'cancel'
GROUP BY care_setting
ORDER BY care_setting;


-- % of bills receiving discounts
Select
    CASE WHEN care_setting is not NULL THEN care_setting
         ELSE 'N/A'
    END,
    count(sale_order.id) as "Number of bill receiving discounts"
FROM sale_order 
WHERE
    discount > 0
    AND date_order >= :'start_date' and date_order <= :'end_date'
    AND sale_order.state != 'cancel'
GROUP BY care_setting
ORDER BY care_setting;



-- % of bills receiving credits
Select
    CASE WHEN care_setting is not NULL THEN care_setting
         ELSE 'N/A'
    END,
    count(sale_order.id) as "Number of bills receiving credits"
FROM
    (Select 
        account_voucher_line.name, move_line_id, amount_original, sum(account_voucher_line.amount) as total_paid, bool_or(reconcile) as reconciled
    from account_voucher_line
    INNER JOIN account_voucher on account_voucher_line.voucher_id = account_voucher.id
    WHERE account_voucher.state != 'cancel'
    group by account_voucher_line.name, move_line_id, amount_original
    order by name
    ) bill_payment
INNER JOIN account_move_line on bill_payment.move_line_id = account_move_line.id
INNER JOIN sale_order on sale_order.name = account_move_line.ref
WHERE
    bill_payment.reconciled = false
    AND date_order >= :'start_date' and date_order <= :'end_date'
    AND sale_order.state != 'cancel'
GROUP BY care_setting
ORDER BY care_setting;
