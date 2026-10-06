package com.datahub.controller;

import com.datahub.dto.UserResponse;
import com.datahub.entity.User;
import com.datahub.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/admin")
public class AdminController {

    private static final Set<String> VALID_ROLES = Set.of("USER", "ADMIN");

    @Autowired
    private UserRepository userRepository;

    @GetMapping("/dashboard")
    public String dashboard() {
        return "Admin Dashboard";
    }

    @GetMapping("/users")
    public List<UserResponse> getAllUsers() {
        // FIX: map to UserResponse instead of returning the raw User entity,
        // which was leaking the bcrypt password hash in the JSON response.
        return userRepository.findAll().stream()
                .map(u -> new UserResponse(u.getId(), u.getUsername(), u.getEmail(), u.getRole()))
                .collect(Collectors.toList());
    }

    @DeleteMapping("/users/{id}")
    public void deleteUser(@PathVariable Long id) {
        userRepository.deleteById(id);
    }

    @PutMapping("/users/{id}/role")
    public UserResponse changeRole(@PathVariable Long id, @RequestParam String role) {
        String normalized = role.toUpperCase();
        // FIX: reject anything that isn't a real role, otherwise hasRole("ADMIN")
        // checks elsewhere in the app can silently break.
        if (!VALID_ROLES.contains(normalized)) {
            throw new RuntimeException("Invalid role: must be USER or ADMIN");
        }
        User user = userRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("User not found"));
        user.setRole(normalized);
        User saved = userRepository.save(user);
        return new UserResponse(saved.getId(), saved.getUsername(), saved.getEmail(), saved.getRole());
    }
}