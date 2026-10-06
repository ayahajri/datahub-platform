package com.datahub.controller;

import com.datahub.entity.Data;
import com.datahub.service.DataService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.data.domain.Page;
import java.util.List;

@RestController

@RequestMapping("/api/data")
public class DataController {

    @Autowired
    private DataService service;


    // CREATE
    @PostMapping
    public Data create(@RequestBody Data data, Authentication auth) {
        return service.create(data, auth.getName());
    }

    // MY DATA
    @GetMapping("/my")
    public List<Data> myData(Authentication auth) {
        return service.getMyData(auth.getName());
    }

    // ALL DATA (ADMIN)
    @GetMapping("/all")
    public List<Data> all() {
        return service.getAll();
    }

    // DELETE
    @DeleteMapping("/{id}")
    public void delete(@PathVariable Long id, Authentication auth) {

        boolean isAdmin = auth.getAuthorities().stream()
                .anyMatch(a -> a.getAuthority().equals("ROLE_ADMIN"));

        service.delete(id, auth.getName(), isAdmin);
    }
    @GetMapping("/my/paginated")
    public Page<Data> myDataPaginated(
            Authentication auth,
            @RequestParam int page,
            @RequestParam int size
    ) {
        return service.getMyDataPaginated(auth.getName(), page, size);
    }
    @GetMapping("/my/search")
    public List<Data> search(
            Authentication auth,
            @RequestParam String keyword
    ) {
        return service.searchMyData(auth.getName(), keyword);
    }
}