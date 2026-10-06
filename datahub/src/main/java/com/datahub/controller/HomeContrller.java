package com.datahub.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

 @RestController
public class HomeContrller {
       
    @GetMapping("/")
    public String home() {
        return "Backend is running OK 🚀";
    }
    

}
