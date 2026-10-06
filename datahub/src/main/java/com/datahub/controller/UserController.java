package com.datahub.controller;

import com.datahub.dto.AuthResponse;
import com.datahub.dto.LoginRequest;
import com.datahub.dto.RegisterRequest;
import com.datahub.dto.UserResponse;
import com.datahub.entity.User;
import com.datahub.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/users")
public class UserController {

    @Autowired
    private UserService userService;

    @PostMapping("/register")
    public UserResponse register(@RequestBody RegisterRequest request) {
        return userService.registerUser(request);
    }

    @PostMapping("/login")
    public AuthResponse login(@RequestBody LoginRequest request) {
        return userService.login(request);
    }
    @GetMapping("/me")
    public String me(Authentication auth) {
        return auth.getName();
    }
}