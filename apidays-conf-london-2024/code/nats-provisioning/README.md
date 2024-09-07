# NATS provisioning

## Install NATS server
In order to use NATS we have to install the NATS server. On Mac OS X, we can use Homebrew to install the NATS server. Here are the instructions:
```bash
brew install nats-server
```

## Install NATS CLI
After installing NATS we will need NATS CLI to ensure that we can run administrative commands. Here are the instructions for installing NATS CLI:
```bash
brew tap nats-io/nats-tools
brew install nats-io/nats-tools/nats
```

## Start NATS server with JetStream enabled
In order to start the NATS server with JetStream enabled, we will need to run the following command:
```bash
nats-server --jetstream
```

## Create a NATS JetStream stream
In order to create a NATS JetStream stream, we will need to run the following command:
```bash
nats stream add "METRICS" --subjects "metrics.>" --retention limits --max-msg-size 1MB --max-bytes 1GB --max-age 1d --storage memory --discard old
```
