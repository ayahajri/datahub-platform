package com.datahub.service;

import com.datahub.entity.Data;
import com.datahub.repository.DataRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class DataService {

    @Autowired
    private DataRepository repository;

    // 🟢 CREATE
    public Data create(Data data, String email) {
        data.setCreatedBy(email);
        return repository.save(data);
    }

    // 🟢 MY DATA (no change)
    public List<Data> getMyData(String email) {
        return repository.findByCreatedBy(email);
    }

    // 🟢 ALL DATA (ADMIN)
    public List<Data> getAll() {
        return repository.findAll();
    }

    // 🟢 DELETE (OWNERSHIP)
    public void delete(Long id, String email, boolean isAdmin) {

        Data data = repository.findById(id)
                .orElseThrow(() -> new RuntimeException("Data not found"));

        if (!isAdmin && !data.getCreatedBy().equals(email)) {
            throw new RuntimeException("Not allowed");
        }

        repository.delete(data);
    }

    // 🔵 PAGINATION (IMPORTANT FIX)
    public Page<Data> getMyDataPaginated(String email, int page, int size) {
        return repository.findByCreatedBy(email, PageRequest.of(page, size));
    }

    // 🔵 SEARCH
    public List<Data> searchMyData(String email, String keyword) {

        return repository.findByCreatedByAndTitleContainingIgnoreCase(email, keyword);
    }
}