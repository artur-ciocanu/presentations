package org.demo.metrics.agent;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class MetricsAgentApplication {

	public static void main(String[] args) {
		SpringApplication.run(MetricsAgentApplication.class, args);
	}

}
