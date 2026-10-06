package com.datahub.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClient;

@Configuration
public class RestClientConfig {

    // Set in application.properties: python.service.url=http://localhost:8000
    @Value("${python.service.url}")
    private String pythonServiceUrl;

    @Bean
    public RestClient pythonServiceRestClient() {
        return RestClient.builder()
                .baseUrl(pythonServiceUrl)
                .build();
    }
}