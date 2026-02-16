package com.example.hub.controller;

import com.example.hub.model.AgentConfig;
import com.example.hub.repository.AgentConfigRepository;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.List;

@RestController
@RequestMapping("/api/v1/agents")
@RequiredArgsConstructor
public class AgentConfigController {

    private final AgentConfigRepository repository;

    @GetMapping
    public List<AgentConfig> listAgents() {
        return repository.findAll();
    }

    @GetMapping("/{agentId}")
    public AgentConfig getAgent(@PathVariable String agentId) {
        return repository.findByAgentId(agentId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "Agent not found: " + agentId));
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public AgentConfig createAgent(@Valid @RequestBody AgentConfig config) {
        if (repository.existsByAgentId(config.getAgentId())) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT, "Agent already exists: " + config.getAgentId());
        }
        config.setUpdatedAt(Instant.now());
        return repository.save(config);
    }

    @PutMapping("/{agentId}")
    public AgentConfig updateAgent(
            @PathVariable String agentId,
            @Valid @RequestBody AgentConfig config) {

        AgentConfig existing = repository.findByAgentId(agentId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "Agent not found: " + agentId));

        config.setId(existing.getId());
        config.setAgentId(agentId);
        config.setUpdatedAt(Instant.now());

        return repository.save(config);
    }

    @DeleteMapping("/{agentId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteAgent(@PathVariable String agentId) {
        AgentConfig existing = repository.findByAgentId(agentId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "Agent not found: " + agentId));
        repository.delete(existing);
    }
}
