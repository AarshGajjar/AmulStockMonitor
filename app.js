document.addEventListener('DOMContentLoaded', () => {
    const statusDiv = document.getElementById('status');
    const controlsDiv = document.getElementById('controls');
    const searchInput = document.getElementById('search-input');
    const selectAllBtn = document.getElementById('select-all');
    const deselectAllBtn = document.getElementById('deselect-all');
    const productListDiv = document.getElementById('product-list');
    const generateBtn = document.getElementById('generate-btn');
    const resultDiv = document.getElementById('result');
    const outputTextarea = document.getElementById('output');
    const copyBtn = document.getElementById('copy-btn');
    const footer = document.querySelector('footer p a');

    // Dynamically set the repo URL in the footer
    const repoUrl = `https://github.com/${window.location.hostname.split('.')[0]}/${window.location.pathname.split('/')[1]}`;
    if (footer && !window.location.hostname.includes('127.0.0.1')) {
        footer.href = repoUrl;
        footer.textContent = repoUrl.replace('https://github.com/', '');
    }

    async function fetchProducts() {
        try {
            const response = await fetch('stock_status.json');
            if (!response.ok) {
                throw new Error(`Failed to fetch stock_status.json. Status: ${response.status}. Make sure the file exists in your repository and the GitHub Action has run at least once.`);
            }
            const products = await response.json();
            const productNames = Object.keys(products).sort();

            if (productNames.length === 0) {
                statusDiv.textContent = 'No products found in stock_status.json. Run the GitHub Action at least once to populate the list.';
                return;
            }

            statusDiv.classList.add('hidden');
            controlsDiv.classList.remove('hidden');
            populateProductList(productNames);
            generateBtn.classList.remove('hidden');

        } catch (error) {
            statusDiv.innerHTML = `<strong>Error:</strong> ${error.message}`;
        }
    }

    function populateProductList(productNames) {
        productListDiv.innerHTML = ''; // Clear existing list
        productNames.forEach(name => {
            const item = document.createElement('div');
            item.className = 'product-item';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = name;
            checkbox.value = name;

            const label = document.createElement('label');
            label.htmlFor = name;
            label.textContent = name.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');

            item.appendChild(checkbox);
            item.appendChild(label);

            // Allow clicking the whole div to toggle the checkbox
            item.addEventListener('click', (e) => {
                if (e.target !== checkbox) {
                    checkbox.checked = !checkbox.checked;
                }
            });

            productListDiv.appendChild(item);
        });
    }

    // --- Search Functionality ---
    searchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        const items = document.querySelectorAll('.product-item');

        items.forEach(item => {
            const label = item.querySelector('label').textContent.toLowerCase();
            if (label.includes(searchTerm)) {
                item.classList.remove('hidden');
            } else {
                item.classList.add('hidden');
            }
        });
    });

    // --- Select All / Deselect All ---
    selectAllBtn.addEventListener('click', () => {
        const visibleCheckboxes = document.querySelectorAll('.product-item:not(.hidden) input[type="checkbox"]');
        visibleCheckboxes.forEach(cb => cb.checked = true);
    });

    deselectAllBtn.addEventListener('click', () => {
        const visibleCheckboxes = document.querySelectorAll('.product-item:not(.hidden) input[type="checkbox"]');
        visibleCheckboxes.forEach(cb => cb.checked = false);
    });

    generateBtn.addEventListener('click', () => {
        const selectedProducts = [];
        const checkboxes = document.querySelectorAll('#product-list input[type="checkbox"]:checked');
        checkboxes.forEach(checkbox => {
            selectedProducts.push(checkbox.value);
        });

        outputTextarea.value = selectedProducts.join(',');
        resultDiv.classList.remove('hidden');
    });

    copyBtn.addEventListener('click', () => {
        outputTextarea.select();
        document.execCommand('copy');
        copyBtn.textContent = 'Copied!';
        setTimeout(() => {
            copyBtn.textContent = 'Copy to Clipboard';
        }, 2000);
    });

    fetchProducts();
});
