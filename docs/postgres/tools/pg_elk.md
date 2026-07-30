# 数据库日志分析

## 数据库日志分析

整体架构

filebeat -> logstash -> elasticseach -> kibana

- filebeat 收集日志
- logstash 中转及日志规则匹配过滤
- elasticsearch 日志存储检索库
- kibana 查看界面


## postgresql

```
log_destination = 'csvlog'
logging_collector = 'on'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_rotation_age = '1d'
log_rotation_size = '100MB'
log_min_messages = 'info'
log_min_duration_statement = '1000'
log_statement = 'ddl'
```


## filebeat 

```
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/lib/pgsql/***/postgresql-*.csv
  fields:
    log_topics: postgresql

  multiline.pattern: '^[[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}.[0-9]{3} [A-Z]{3}'
  multiline.negate: true
  multiline.match: after
filebeat.config.modules:
  path: ${path.config}/modules.d/*.yml
  reload.enabled: false
setup.template.settings:
  index.number_of_shards: 1
tags: ["postgesql"]
setup.kibana:
output.logstash:
  hosts: ["*.*.*.*:5044"]
processors:
  - add_host_metadata: ~
  - add_cloud_metadata: ~
```


## logstash

```
#
# this config is use for version logstash 7.3.1
#

input {
  beats {
    port => 5044
  }

  #sdtin{
  #
  #}

}


# The filter part of this file is commented out to indicate that it
# is optional.

# use csv plugin against pglog , pglog neet set log format to csv first.
filter {
  csv {
    columns => [
      "log_time",
      "user_name",
      "database_name",
      "process_id",
      "connection_from",
      "session_id",
      "session_line_num",
      "command_tag",
      "session_start_time",
      "virtual_transaction_id",
      "transaction_id",
      "error_severity",
      "sql_state_code",
      "message",
      "detail",
      "hint",
      "internal_query",
      "internal_query_pos",
      "context",
      "query",
      "query_pos",
      "location",
      "application_name"
    ]
  }
}

#
# different log type out put different log format
# 1. log duration log
# 2. norm log statment
# 3. checkpint log
# 4. other
filter {
 if [message] =~ /duration: [0-9]{1,8}[.]{0,1}[0-9]{1,5} ms/ {
     mutate {
         split => { "message" => "statement:" }
         add_field => {"duration" => "%{[message][0]}"}
         add_field => {"statement" => "%{[message][1]}"}
     }
    mutate { gsub => [ "duration", "duration: ", "" ] }
    mutate { gsub => [ "duration", " ms", "" ] }
    mutate { convert => { "duration" => "float" } }
    mutate {
      add_field => {"sqltype" =>  "slowsql" }
      remove_field => "message"
   }
  } else if [message] =~ /statement: / {
    mutate { gsub => [ "message", "statement: ", "" ] }
    mutate { rename => {"message" => "statement"}}
    mutate {add_field => { "sqltype" => "statementsql" } }
  } else if [message] =~ /checkpoint / {
    mutate {add_field => { "sqltype" => "checkpoint" } }
    mutate { rename => {"message" => "statement"}}
  } else{
    mutate {add_field => { "sqltype" => "other" } }
  }

  mutate { remove_field => [
    "connection_from",
    "session_line_num",
    "command_tag",
    "session_start_time",
    "virtual_transaction_id",
    "transaction_id",
    "error_severity",
    "sql_state_code",
    "detail",
    "hint",
    "internal_query",
    "internal_query_pos",
    "context",
    "query",
    "query_pos",
    "location",
    "application_name",
    "source",
    "input_type"
  ] }
}

output {
# file {
#   path => "/etc/logstash/pg.log"
#   codec => line { format => "custom format: %{message}"}
# }

#   for debug

#    stdout {
#        codec => rubydebug
#    }


 elasticsearch {
   hosts => "*.*.*.*:9200"
#   manage_template => false
   template_name => "postgres_template"
   index => "%{[@metadata][beat]}-%{[@metadata][version]}-%{+YYYY.MM.dd}"
   #user => "elastic"
   #password => "123456"
 }
}
```


