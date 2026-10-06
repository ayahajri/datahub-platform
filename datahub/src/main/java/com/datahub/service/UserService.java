package com.datahub.service;

import com.datahub.dto.AuthResponse;
import com.datahub.dto.LoginRequest;
import com.datahub.dto.RegisterRequest;
import com.datahub.dto.UserResponse;
import com.datahub.entity.User;
import com.datahub.repository.UserRepository;
import com.datahub.security.JwtUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

@Service
public class UserService {

    @Autowired
    private UserRepository userRepository;
    @Autowired
    private PasswordEncoder passwordEncoder;
    @Autowired
    private JwtUtil jwtUtil;

    public AuthResponse login(LoginRequest request) {
        // FIX: same error message whether the email doesn't exist or the
        // password is wrong, so attackers can't use this endpoint to find
        // out which emails are registered.
        User user = userRepository.findByEmail(request.getEmail())
                .orElseThrow(() -> new RuntimeException("Invalid email or password"));

        if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
            throw new RuntimeException("Invalid email or password");
        }

        String token = jwtUtil.generateToken(user.getEmail(), user.getRole());
        return new AuthResponse(token, user.getRole());
    }

    public UserResponse registerUser(RegisterRequest request) {
        // FIX: give a clear error instead of letting the DB unique constraint
        // throw an ugly, unhandled exception.
        if (userRepository.findByEmail(request.getEmail()).isPresent()) {
            throw new RuntimeException("Email already registered");
        }

        User user = new User();
        user.setUsername(request.getUsername());
        user.setEmail(request.getEmail());
        user.setPassword(passwordEncoder.encode(request.getPassword()));
        user.setRole("USER"); // hardcoded on purpose: clients can never self-assign ADMIN
        User saved = userRepository.save(user);
        return new UserResponse(saved.getId(), saved.getUsername(), saved.getEmail(), saved.getRole());
    }
}