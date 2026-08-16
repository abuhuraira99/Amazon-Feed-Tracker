document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('fileInput');
    const chooseFileBtn = document.getElementById('chooseFileBtn');
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const uploadBtn = document.getElementById('uploadBtn');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const statusText = document.getElementById('statusText');
    const rowStats = document.getElementById('rowStats');
    const totalRowsCount = document.getElementById('totalRowsCount');

    const actionsSection = document.getElementById('actionsSection');
    const tableSection = document.getElementById('tableSection');
    const changesTableBody = document.getElementById('changesTableBody');
    const pushChangesBtn = document.getElementById('pushChangesBtn');

    const btnInStock = document.getElementById('btnInStock');
    const btnOutStock = document.getElementById('btnOutStock');
    const btnPriceChanged = document.getElementById('btnPriceChanged');
    const btnNewProducts = document.getElementById('btnNewProducts');

    // Handle File Selection
    chooseFileBtn.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            fileNameDisplay.textContent = fileInput.files[0].name;
            uploadBtn.disabled = false;
        } else {
            fileNameDisplay.textContent = 'No file selected';
            uploadBtn.disabled = true;
        }
    });

    // Handle Upload & Compare
    uploadBtn.addEventListener('click', async () => {
        if (fileInput.files.length === 0) return;

        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('file', file);

        // UI Updates for uploading
        uploadBtn.disabled = true;
        chooseFileBtn.disabled = true;
        progressContainer.style.display = 'block';
        progressBar.style.width = '50%';
        statusText.textContent = 'Uploading and processing... This may take a minute for large files.';
        statusText.style.color = 'var(--accent-color)';
        rowStats.classList.add('hidden');
        
        // Reset push button for the new file
        pushChangesBtn.textContent = 'Push Changes to Database';
        pushChangesBtn.style.background = '';
        pushChangesBtn.disabled = true;

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                progressBar.style.width = '100%';
                statusText.textContent = 'Processing complete!';
                statusText.style.color = 'var(--success-color)';
                
                totalRowsCount.textContent = data.total_rows.toLocaleString();
                rowStats.classList.remove('hidden');
                
                if (data.is_initial) {
                    statusText.textContent = 'Initial feed processed. No previous data to compare. Ready to Push Changes.';
                } else {
                    // Update download links
                    btnInStock.href = `/download/${data.in_stock_file}`;
                    btnOutStock.href = `/download/${data.out_of_stock_file}`;
                    btnPriceChanged.href = `/download/${data.price_changed_file}`;
                    btnNewProducts.href = `/download/${data.new_products_file}`;
                    
                    actionsSection.classList.remove('hidden');
                }

                // Render Table Pages
                allChanges = data.changes;
                currentPage = 1;
                renderTablePage();
                tableSection.classList.remove('hidden');
                
                // Re-enable the push button so the user can click it
                pushChangesBtn.disabled = false;

            } else {
                throw new Error(data.error || 'Failed to process file');
            }
        } catch (error) {
            progressBar.style.width = '0%';
            statusText.textContent = `Error: ${error.message}`;
            statusText.style.color = 'var(--error-color)';
        } finally {
            uploadBtn.disabled = false;
            chooseFileBtn.disabled = false;
        }
    });

    // Handle Push Changes
    pushChangesBtn.addEventListener('click', async () => {
        pushChangesBtn.disabled = true;
        pushChangesBtn.textContent = 'Pushing...';

        try {
            const response = await fetch('/push', { method: 'POST' });
            const data = await response.json();

            if (response.ok) {
                alert('Database successfully updated!');
                pushChangesBtn.textContent = 'Pushed Successfully';
                pushChangesBtn.style.background = 'var(--success-color)';
            } else {
                throw new Error(data.error || 'Failed to push changes');
            }
        } catch (error) {
            alert(`Error: ${error.message}`);
            pushChangesBtn.disabled = false;
            pushChangesBtn.textContent = 'Push Changes to Database';
        }
    });

    let allChanges = [];
    let currentPage = 1;
    const itemsPerPage = 50;

    const prevPageBtn = document.getElementById('prevPageBtn');
    const nextPageBtn = document.getElementById('nextPageBtn');
    const pageInfo = document.getElementById('pageInfo');

    function renderTablePage() {
        changesTableBody.innerHTML = '';
        
        if (allChanges.length === 0) {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td colspan="4" style="text-align: center; color: var(--text-secondary);">No changes detected.</td>`;
            changesTableBody.appendChild(tr);
            pageInfo.textContent = 'Page 1 of 1';
            prevPageBtn.disabled = true;
            nextPageBtn.disabled = true;
            return;
        }

        const totalPages = Math.ceil(allChanges.length / itemsPerPage);
        if (currentPage > totalPages) currentPage = totalPages;
        if (currentPage < 1) currentPage = 1;

        const startIdx = (currentPage - 1) * itemsPerPage;
        const endIdx = startIdx + itemsPerPage;
        const pageItems = allChanges.slice(startIdx, endIdx);

        pageItems.forEach(change => {
            const tr = document.createElement('tr');
            
            let badgeClass = '';
            if (change.change_type === 'In Stock') badgeClass = 'badge-instock';
            else if (change.change_type === 'Out of Stock') badgeClass = 'badge-outstock';
            else if (change.change_type === 'Price Changed') badgeClass = 'badge-price';
            else if (change.change_type === 'New Product') badgeClass = 'badge-instock';

            tr.innerHTML = `
                <td>${change.barcode}</td>
                <td>${change.title}</td>
                <td><span class="badge ${badgeClass}">${change.change_type}</span></td>
                <td>${change.details}</td>
            `;
            changesTableBody.appendChild(tr);
        });

        pageInfo.textContent = `Page ${currentPage} of ${totalPages} (${allChanges.length} total changes)`;
        prevPageBtn.disabled = currentPage === 1;
        nextPageBtn.disabled = currentPage === totalPages;
    }

    prevPageBtn.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            renderTablePage();
        }
    });

    nextPageBtn.addEventListener('click', () => {
        const totalPages = Math.ceil(allChanges.length / itemsPerPage);
        if (currentPage < totalPages) {
            currentPage++;
            renderTablePage();
        }
    });

    // Handle Search
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const searchResult = document.getElementById('searchResult');

    searchBtn.addEventListener('click', async () => {
        const barcode = searchInput.value.trim();
        if (!barcode) return;
        
        searchBtn.disabled = true;
        searchBtn.textContent = 'Searching...';
        
        try {
            const response = await fetch(`/search/${encodeURIComponent(barcode)}`);
            const data = await response.json();
            
            searchResult.classList.remove('hidden');
            
            if (data.success) {
                const p = data.product;
                let stockStatus = p.stock > 0 ? `<span style="color:var(--success-color)">In Stock (${p.stock})</span>` : `<span style="color:var(--error-color)">Out of Stock (0)</span>`;
                
                searchResult.innerHTML = `
                    <h3>Product Found</h3>
                    <div class="result-grid">
                        <div class="result-item"><span class="result-label">Barcode</span><span class="result-value">${p.barcode}</span></div>
                        <div class="result-item" style="grid-column: span 2"><span class="result-label">Title</span><span class="result-value">${p.title}</span></div>
                        <div class="result-item"><span class="result-label">Artist</span><span class="result-value">${p.artist || 'N/A'}</span></div>
                        <div class="result-item"><span class="result-label">Price</span><span class="result-value">$${p.price.toFixed(2)}</span></div>
                        <div class="result-item"><span class="result-label">Stock</span><span class="result-value">${stockStatus}</span></div>
                        <div class="result-item"><span class="result-label">Format</span><span class="result-value">${p.format || 'N/A'}</span></div>
                    </div>
                `;
            } else {
                searchResult.innerHTML = `<div style="color:var(--error-color)">${data.message}</div>`;
            }
        } catch (error) {
            searchResult.classList.remove('hidden');
            searchResult.innerHTML = `<div style="color:var(--error-color)">Error searching database.</div>`;
        } finally {
            searchBtn.disabled = false;
            searchBtn.textContent = 'Search';
        }
    });
});
