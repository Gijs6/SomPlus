# SomPlus

Monitors your Somtoday for grade and schedule changes and sends you notifications via Pushsafer or Discord.

## Running with Docker

```bash
mkdir -p somplus/config/users somplus/data somplus/logs
```

Copy the example configs from [CONFIG.md](CONFIG.md), fill in your credentials (refresh token + leerling id from Som), then:

```bash
docker run -d --name somplus --restart unless-stopped \
  -v somplus/config:/app/config:ro \
  -v somplus/data:/app/data \
  -v somplus/logs:/app/logs \
  ghcr.io/gijs6/somplus:latest
```

## Troubleshooting

- The most common problem is Somtoday revoking your token. You will simply have to provide Somplus with a new one.
- If you get your Somtoday token from another place than the local storage on the Somtoday portal, you may need to change the `client_id` in the config.

Since the behaviour of Somtoday can differ widely between schools (and the new Somtoday API is not documented), using this for any other school than my own could result in some problems.

## Config options

See [CONFIG.md](CONFIG.md) for config examples and options.
