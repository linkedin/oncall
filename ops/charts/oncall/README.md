# Oncall chart

Oncall is a calendar tool designed for scheduling and managing on-call shifts. It is a standalone application that serves as source of truth for dynamic ownership information as well as contact info.


## Installing the Chart
To install the chart with the release name `oncall-release`:
```
cd ops/charts/oncall
helm3 dep update
helm3 install oncall-release .
```

## Parameters

### Port parameters

| Parameter          | Description              | Default |
|--------------------|--------------------------|---------|
| `port.external`    | External port for OnCall | `80`    |
| `port.internal`    | Internal port for OnCall | `8080`  |

### Config parameters

| Parameter                             | Description                                    | Default      |
|---------------------------------------|------------------------------------------------|--------------|
| `config.auth.debug`                   | Debug mode toggle, disable in production       | `true`       |
| `config.auth.module`                  | Auth module where Authenticator is implemented | `debug`      |
| `config.auth.ldap.ldap_url`           | LDAP url                                       | `nil`        |
| `config.auth.ldap.ldap_user_suffix`   | LDAP user suffix                               | `nil`        |
| `config.auth.ldap.ldap_bind_user`     | LDAP bind user                                 | `nil`        |
| `config.auth.ldap.ldap_bind_password` | LDAP bind password                             | `nil`        |
| `config.auth.ldap.ldap_base_dn`       | LDAP base dn                                   | `nil`        |
| `config.auth.ldap.ldap_search_filter` | LDAP search filter                             | `nil`        |
| `config.auth.ldap.import_user`        | User import from LDAP on login                 | `nil`        |
| `config.auth.ldap.attrs.username`     | Variable name for username in LDAP             | `nil`        |
| `config.auth.ldap.attrs.full_name`    | Variable name for user full name in LDAP       | `nil`        |
| `config.auth.ldap.attrs.email`        | Variable name for user email in LDAP           | `nil`        |
| `config.auth.ldap.attrs.call`         | Variable name for user phone contact in LDAP   | `nil`        |
| `config.auth.ldap.attrs.sms`          | Variable name for user sms contact in LDAP     | `nil`        |
| `config.auth.ldap.attrs.slack`        | Variable name for user slack in LDAP           | `nil`        |
| `config.timezone`                     | Default timezone                               | `US/Pacific` |

### Ingress parameters

| Parameter             | Description                           | Default        |
|-----------------------|---------------------------------------|----------------|
| `ingress.enabled`     | Enable ingress controller resource    | `false`        |
| `ingress.class`       | Class used in ingress controller      | `nginx`        |
| `ingress.certManager` | Add annotations for cert-manager      | `true`         |
| `ingress.hostname`    | Default host for the ingress resource | `oncall.local` |
| `ingress.tls`         | TLS status in ingress controller      | `true`         |

### Database parameters

| Parameter                        | Description                          | Default |
|----------------------------------|--------------------------------------|---------|
| `dbInitialized`                  | Is database initialized              | `false` |
| `mysql.auth.rootPassword`        | Password for the root user           | `1234`  |
| `mysql.primary.persistence.size` | MySQL primary persistent volume size | `1Gi`   |
