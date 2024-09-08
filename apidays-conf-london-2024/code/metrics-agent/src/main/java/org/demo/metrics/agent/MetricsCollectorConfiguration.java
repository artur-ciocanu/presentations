package org.demo.metrics.agent;

import io.cloudevents.core.format.ContentType;
import io.cloudevents.core.format.EventFormat;
import io.cloudevents.core.provider.EventFormatProvider;
import io.nats.client.Connection;
import io.nats.client.JetStream;
import io.nats.client.Nats;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClient;

import java.io.IOException;

@Configuration
public class MetricsCollectorConfiguration {
    private static final String NATS_URL = "nats://localhost:4222";
    private static final String APP_METRICS_URL = "http://localhost:8080/metrics";

    @Bean
    public RestClient restClient() {
        return RestClient.builder()
            .baseUrl(APP_METRICS_URL)
            .build();
    }

    @Bean
    public EventFormat eventFormat() {
        return EventFormatProvider.getInstance().resolveFormat(ContentType.JSON);
    }

    @Bean
    public Connection connection() throws IOException, InterruptedException {
        return Nats.connect(NATS_URL);
    }

    @Bean
    public JetStream jetStream(Connection natsConnection) throws IOException {
        return natsConnection.jetStream();
    }
}
