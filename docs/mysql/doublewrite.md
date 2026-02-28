```
show variables like '%double%';
+-------------------------------+-------+
| Variable_name                 | Value |
+-------------------------------+-------+
| innodb_doublewrite            | ON    |
| innodb_doublewrite_batch_size | 0     |
| innodb_doublewrite_dir        |       |
| innodb_doublewrite_files      | 2     |
| innodb_doublewrite_pages      | 4     |
+-------------------------------+-------


show status like '%lwr%';
+----------------------------+---------+
| Variable_name              | Value   |
+----------------------------+---------+
| Innodb_dblwr_pages_written | 6339188 |
| Innodb_dblwr_writes        | 1991962 |
+----------------------------+---------+
```
