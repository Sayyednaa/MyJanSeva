/* ==========================================================================
   AgriCard - Application Logic & IndexedDB Operations
   ========================================================================== */

// Global App State
let db = null;
let currentEditingId = null; // null if creating a new record, number if editing
let printQueue = []; // Array of card objects currently in queue
let historyCards = []; // Cache of all history cards from DB
const placeholderAvatar = window.PLACEHOLDER_AVATAR_URL || '/static/id_cards/farmer_id/placeholder-avatar.png';
let selectedDesign = '1';

function chargeWallet(slug, quantity) {
    if (!window.WALLET_CHARGE_URL || !window.CSRF_TOKEN) {
        return Promise.reject(new Error('Wallet integration not configured.'));
    }
    let formData = new FormData();
    formData.append('service_slug', slug);
    formData.append('quantity', quantity);
    formData.append('csrfmiddlewaretoken', window.CSRF_TOKEN);
    return fetch(window.WALLET_CHARGE_URL, {method: 'POST', body: formData})
        .then(r => r.json())
        .then(json => {
            if(json.status === 'error') {
                let err = new Error(json.message);
                if (json.code === 'insufficient_balance') {
                    err.isInsufficientBalance = true;
                    err.redirectUrl = json.redirect_url || '/wallet/topup/';
                }
                throw err;
            }
            return json;
        });
}

// Initialize Application on Page Load
document.addEventListener('DOMContentLoaded', async () => {

  // 1. Initialize Icons
  if (typeof lucide !== 'undefined') {
    lucide.createIcons();
  }

  // 2. Initialize IndexedDB
  try {
    db = await initDB();
    await loadHistory();
    loadPrintQueueFromStorage();
  } catch (error) {
    console.error('Database initialization failed:', error);
    alert('Failed to initialize local database. Using mock memory storage instead.');
    setupMockDB();
  }

  // 3. Setup Default Form State & Initial Row
  resetForm();

  // 4. Attach Event Listeners
  setupEventListeners();
});

/* ==========================================================================
   INDEXEDDB DATABASE LAYER
   ========================================================================== */
function initDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('AgriCardDB', 1);

    request.onerror = (event) => reject(event.target.error);
    request.onsuccess = (event) => resolve(event.target.result);

    request.onupgradeneeded = (event) => {
      const dbInstance = event.target.result;
      if (!dbInstance.objectStoreNames.contains('cards')) {
        dbInstance.createObjectStore('cards', { keyPath: 'id', autoIncrement: true });
      }
    };
  });
}

// Memory fallback in case IndexedDB fails (e.g. private browser mode restriction)
function setupMockDB() {
  const mockStorage = {
    cards: [],
    nextId: 1
  };
  
  db = {
    transaction: (storeNames, mode) => {
      return {
        objectStore: (name) => ({
          getAll: () => ({
            onsuccess: null,
            addEventListener: function(type, cb) {
              if(type === 'success') {
                setTimeout(() => cb({ target: { result: mockStorage.cards } }), 50);
              }
            }
          }),
          add: (data) => {
            const copy = { ...data, id: mockStorage.nextId++ };
            mockStorage.cards.push(copy);
            return {
              onsuccess: null,
              addEventListener: function(type, cb) {
                if(type === 'success') setTimeout(() => cb({ target: { result: copy.id } }), 50);
              }
            };
          },
          put: (data) => {
            const index = mockStorage.cards.findIndex(c => c.id === data.id);
            if(index !== -1) mockStorage.cards[index] = data;
            return {
              onsuccess: null,
              addEventListener: function(type, cb) {
                if(type === 'success') setTimeout(() => cb({ target: { result: data.id } }), 50);
              }
            };
          },
          delete: (id) => {
            mockStorage.cards = mockStorage.cards.filter(c => c.id !== id);
            return {
              onsuccess: null,
              addEventListener: function(type, cb) {
                if(type === 'success') setTimeout(() => cb({}), 50);
              }
            };
          }
        }),
        oncomplete: null,
        onerror: null
      };
    }
  };
}

function getAllCards() {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(['cards'], 'readonly');
    const store = transaction.objectStore('cards');
    const request = store.getAll();

    request.onsuccess = (event) => resolve(event.target.result || []);
    request.onerror = (event) => reject(event.target.error);
  });
}

function saveCard(cardData) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(['cards'], 'readwrite');
    const store = transaction.objectStore('cards');
    
    let request;
    if (cardData.id) {
      request = store.put(cardData);
    } else {
      request = store.add(cardData);
    }

    request.onsuccess = (event) => resolve(event.target.result);
    request.onerror = (event) => reject(event.target.error);
  });
}

function deleteCardFromDB(id) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(['cards'], 'readwrite');
    const store = transaction.objectStore('cards');
    const request = store.delete(id);

    request.onsuccess = () => resolve();
    request.onerror = (event) => reject(event.target.error);
  });
}

/* ==========================================================================
   APP EVENT LISTENERS
   ========================================================================== */
function setupEventListeners() {
  // Navigation Tabs Switcher
  const navButtons = document.querySelectorAll('.nav-btn');
  navButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabName = btn.getAttribute('data-tab');
      switchTab(tabName);
    });
  });



  // Dynamic Land Table Actions
  document.getElementById('add-table-row').addEventListener('click', () => {
    addLandTableRow();
  });

  // Form Field Sync Events
  const syncFields = ['farmer-id', 'name-en', 'name-hi', 'dob', 'gender', 'mobile', 'aadhaar', 'address'];
  syncFields.forEach(fieldId => {
    const el = document.getElementById(fieldId);
    el.addEventListener('input', updateLivePreview);
    el.addEventListener('change', updateLivePreview);
  });

  // Photo Upload Handler
  const photoInput = document.getElementById('photo-upload');
  const uploadZone = document.querySelector('.photo-upload-zone');
  
  photoInput.addEventListener('change', handlePhotoSelection);
  
  // Drag and Drop photo support
  uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.style.borderColor = 'var(--primary-light)';
    uploadZone.style.backgroundColor = 'rgba(64, 145, 108, 0.05)';
  });
  
  uploadZone.addEventListener('dragleave', () => {
    uploadZone.style.borderColor = '#cbd5e1';
    uploadZone.style.backgroundColor = '#f8fafc';
  });
  
  uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.style.borderColor = '#cbd5e1';
    uploadZone.style.backgroundColor = '#f8fafc';
    if (e.dataTransfer.files.length) {
      photoInput.files = e.dataTransfer.files;
      handlePhotoSelection();
    }
  });

  // Remove Photo Button
  document.querySelector('.remove-photo-btn').addEventListener('click', (e) => {
    e.stopPropagation();
    removeUploadedPhoto();
  });

  // Reset/Clear Form Button
  document.getElementById('clear-form').addEventListener('click', () => {
    if(confirm('Are you sure you want to clear the form?')) {
      resetForm();
    }
  });

  // Submit/Save Form Button
  document.getElementById('farmer-form').addEventListener('submit', handleFormSubmit);

  // History Actions: Search filter
  document.getElementById('history-search').addEventListener('input', filterHistoryList);

  // History Actions: Checkbox Selection
  document.getElementById('select-all-records').addEventListener('change', toggleAllRecordsSelection);
  document.getElementById('btn-bulk-queue').addEventListener('click', bulkQueueSelected);
  document.getElementById('btn-bulk-delete').addEventListener('click', bulkDeleteSelected);

  // Queue actions
  document.getElementById('clear-queue').addEventListener('click', () => {
    if(confirm('Are you sure you want to clear the print queue?')) {
      printQueue = [];
      savePrintQueueToStorage();
      renderPrintQueue();
      updateBadges();
    }
  });
  document.getElementById('trigger-batch-print').addEventListener('click', printQueueA4Layout);

  // Preview quick actions
  document.getElementById('print-single-card').addEventListener('click', printSingleCardDirectly);
  document.getElementById('add-to-queue-btn').addEventListener('click', addCurrentCardToQueue);

  // PDF Upload Event Listeners
  const pdfInput = document.getElementById('pdf-upload');
  const pdfZone = document.getElementById('pdf-upload-zone');
  
  if (pdfInput && pdfZone) {
    pdfInput.addEventListener('change', handlePdfFileSelect);
    
    pdfZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      pdfZone.closest('.pdf-upload-container').classList.add('dragover');
    });
    
    pdfZone.addEventListener('dragleave', () => {
      pdfZone.closest('.pdf-upload-container').classList.remove('dragover');
    });
    
    pdfZone.addEventListener('drop', (e) => {
      e.preventDefault();
      pdfZone.closest('.pdf-upload-container').classList.remove('dragover');
      if (e.dataTransfer.files.length) {
        pdfInput.files = e.dataTransfer.files;
        handlePdfFileSelect();
      }
    });
  }

  // Design Select listener
  const designSelect = document.getElementById('design-select');
  if (designSelect) {
    const savedDesign = localStorage.getItem('agri_card_design') || '1';
    designSelect.value = savedDesign;
    selectedDesign = savedDesign;
    setTimeout(() => { applyCardDesign(savedDesign); }, 100);

    designSelect.addEventListener('change', (e) => {
      const design = e.target.value;
      selectedDesign = design;
      localStorage.setItem('agri_card_design', design);
      applyCardDesign(design);
    });
  }
}

function applyCardDesign(design) {
  const frontCard = document.getElementById('live-card-front');
  const backCard = document.getElementById('live-card-back');
  if (frontCard && backCard) {
    // Remove all design classes
    frontCard.classList.remove('design-2-front', 'design-3-front');
    backCard.classList.remove('design-2-back', 'design-3-back');
    // Apply selected design (design 1 = default, no class needed)
    if (design === '2') {
      frontCard.classList.add('design-2-front');
      backCard.classList.add('design-2-back');
    } else if (design === '3') {
      frontCard.classList.add('design-3-front');
      backCard.classList.add('design-3-back');
    }
  }
}

/* ==========================================================================
   TABS MANAGEMENT
   ========================================================================== */
function switchTab(tabId) {
  // Update nav buttons
  const navButtons = document.querySelectorAll('.nav-btn');
  navButtons.forEach(btn => {
    if (btn.getAttribute('data-tab') === tabId) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  // Update tabs visibility
  const tabs = document.querySelectorAll('.tab-content');
  tabs.forEach(tab => {
    if (tab.id === `${tabId}-tab`) {
      tab.classList.add('active');
    } else {
      tab.classList.remove('active');
    }
  });

  // Special tab loads
  if (tabId === 'history') {
    loadHistory();
  } else if (tabId === 'print-queue') {
    renderPrintQueue();
  }
}

function updateBadges() {
  document.getElementById('history-count').innerText = historyCards.length;
  document.getElementById('queue-count').innerText = printQueue.length;
  
  // Update selected count checkbox badge
  const selectedCount = document.querySelectorAll('.record-checkbox:checked').length;
  document.getElementById('selected-count').innerText = selectedCount;
}

/* ==========================================================================
   FORM & LAND TABLE CONTROLLER
   ========================================================================== */
function generateFarmerId() {
  
  return '';
}

function resetForm() {
  currentEditingId = null;
  document.getElementById('farmer-form').reset();
  
  // Set default generated ID
  document.getElementById('farmer-id').value = generateFarmerId();
  
  // Set default Date of Birth (say 30 years ago)
  const defaultDob = new Date();
  defaultDob.setFullYear(defaultDob.getFullYear() - 30);
  document.getElementById('dob').value = defaultDob.toISOString().split('T')[0];

  // Remove Photo & Reset Preview
  removeUploadedPhoto();

  // Clear and reset Land Table to 1 empty row
  const tableBody = document.querySelector('#field-details-table tbody');
  tableBody.innerHTML = '';
  addLandTableRow('UTTAR PRADESH', 'SIDDHARTH NAGAR', 'Madhwapur Kalan', '124', '*', '0.150000');

  updateLivePreview();
}

function addLandTableRow(state = 'UTTAR PRADESH', dist = 'SIDDHARTH NAGAR', vill = '', sno = '', ss = '*', area = '') {
  const tableBody = document.querySelector('#field-details-table tbody');
  const rowId = 'row_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5);
  
  const tr = document.createElement('tr');
  tr.id = rowId;
  tr.innerHTML = `
    <td><input type="text" class="input-state" placeholder="e.g. UTTAR PRADESH" value="${state}" required></td>
    <td><input type="text" class="input-dist" placeholder="e.g. SIDDHARTH NAGAR" value="${dist}" required></td>
    <td><input type="text" class="input-vill" placeholder="e.g. Birdpur" value="${vill}" required></td>
    <td><input type="text" class="input-sno" placeholder="e.g. 124" value="${sno}" required></td>
    <td><input type="text" class="input-ss" placeholder="e.g. *" value="${ss}" required></td>
    <td><input type="number" step="0.000001" class="input-area" placeholder="e.g. 0.150000" value="${area}" required></td>
    <td>
      <button type="button" class="btn btn-danger btn-sm btn-icon delete-row-btn" title="Remove Row">
        <i data-lucide="minus"></i>
      </button>
    </td>
  `;
  
  // Add row-specific event listeners for real-time updates
  const inputs = tr.querySelectorAll('input');
  inputs.forEach(inp => {
    inp.addEventListener('input', updateLivePreview);
  });

  tr.querySelector('.delete-row-btn').addEventListener('click', () => {
    tr.remove();
    updateLivePreview();
  });

  tableBody.appendChild(tr);
  if (typeof lucide !== 'undefined') {
    lucide.createIcons({ attrs: { class: 'lucide' } });
  }
  updateLivePreview();
}

function getLandTableData() {
  const data = [];
  const rows = document.querySelectorAll('#field-details-table tbody tr');
  rows.forEach(row => {
    data.push({
      state: row.querySelector('.input-state').value.toUpperCase(),
      dist: row.querySelector('.input-dist').value,
      vill: row.querySelector('.input-vill').value,
      sNo: row.querySelector('.input-sno').value,
      ss: row.querySelector('.input-ss').value,
      area: parseFloat(row.querySelector('.input-area').value || 0).toFixed(6)
    });
  });
  return data;
}

/* ==========================================================================
   PHOTO UPLOAD OPERATIONS
   ========================================================================== */
function handlePhotoSelection() {
  const fileInput = document.getElementById('photo-upload');
  const previewImg = document.getElementById('photo-preview-img');
  const uploadPlaceholder = document.querySelector('.upload-placeholder');
  const removeBtn = document.querySelector('.remove-photo-btn');
  
  if (fileInput.files && fileInput.files[0]) {
    const file = fileInput.files[0];
    
    // Scale and compress the photo
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        // Target max height/width = 300px
        const maxDim = 300;
        let w = img.width;
        let h = img.height;
        if (w > h) {
          if (w > maxDim) {
            h = Math.round((h * maxDim) / w);
            w = maxDim;
          }
        } else {
          if (h > maxDim) {
            w = Math.round((w * maxDim) / h);
            h = maxDim;
          }
        }
        
        const canvas = document.createElement('canvas');
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, w, h);
        
        // Output as compact JPEG
        const base64Photo = canvas.toDataURL('image/jpeg', 0.85);
        
        previewImg.src = base64Photo;
        previewImg.classList.remove('hidden');
        uploadPlaceholder.classList.add('hidden');
        removeBtn.classList.remove('hidden');
        
        // Sync live preview
        document.getElementById('card-photo').src = base64Photo;
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  }
}


function removeUploadedPhoto() {
  document.getElementById('photo-upload').value = '';
  
  const previewImg = document.getElementById('photo-preview-img');
  const uploadPlaceholder = document.querySelector('.upload-placeholder');
  const removeBtn = document.querySelector('.remove-photo-btn');
  
  previewImg.src = '';
  previewImg.classList.add('hidden');
  uploadPlaceholder.classList.remove('hidden');
  removeBtn.classList.add('hidden');
  
  // Reset live preview to placeholder
  document.getElementById('card-photo').src = placeholderAvatar;
}

/* ==========================================================================
   LIVE CARD PREVIEW CONTROLLER & QR ENGINE
   ========================================================================== */
let qrCodeGenerator = null;

function updateLivePreview() {
  // 1. Core Fields
  const fId = document.getElementById('farmer-id').value;
  const nameEn = document.getElementById('name-en').value || 'Sita Kumari';
  const nameHi = document.getElementById('name-hi').value || 'सीता कुमारी';
  
  // Format Date of Birth
  const dobInput = document.getElementById('dob').value;
  let formattedDob = '01/01/2060';
  if (dobInput) {
    const parts = dobInput.split('-');
    if (parts.length === 3) {
      formattedDob = `${parts[2]}/${parts[1]}/${parts[0]}`;
    }
  }
  
  const gender = document.getElementById('gender').value;
  const mobile = document.getElementById('mobile').value || '8700353999';
  
  // Format Aadhaar: XXXX XXXX 1234 (only if present)
  const aadhaarVal = document.getElementById('aadhaar').value;
  const aadhaarLabel = document.getElementById('card-aadhaar-label');
  const aadhaarDisplay = document.getElementById('card-aadhaar');
  if (aadhaarVal && aadhaarVal.length >= 4) {
    let formattedAadhaar = aadhaarVal.length === 12
      ? `XXXX XXXX ${aadhaarVal.substr(8, 4)}`
      : aadhaarVal;
    aadhaarLabel.style.display = '';
    aadhaarDisplay.style.display = '';
    aadhaarDisplay.innerText = formattedAadhaar;
  } else {
    aadhaarLabel.style.display = 'none';
    aadhaarDisplay.style.display = 'none';
    aadhaarDisplay.innerText = '';
  }

  const address = document.getElementById('address').value || 'Village- Youtube, Post-Video puri, Dist.-Shivani pur, Bihar';

  // 2. Set Preview Front Card Values
  document.getElementById('card-farmer-id').innerText = fId;
  document.getElementById('card-name-en').innerText = nameEn;
  document.getElementById('card-name-hi').innerText = nameHi;
  document.getElementById('card-dob').innerText = formattedDob;
  document.getElementById('card-gender').innerText = gender;
  document.getElementById('card-mobile').innerText = mobile;

  // 3. Set Preview Back Card Values
  document.getElementById('card-address').innerText = address;

  // 4. Update Land details Table in Card Back
  const landData = getLandTableData();
  const cardTableBody = document.querySelector('#card-field-table tbody');
  cardTableBody.innerHTML = '';
  
  // Max out land detail preview to 4 rows on the card to fit dimensions safely.
  const previewRows = landData.slice(0, 4);
  
  if (previewRows.length === 0) {
    // Add placeholder empty row
    cardTableBody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #aaa;">No land data added</td></tr>`;
  } else {
    previewRows.forEach(row => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${row.state || '-'}</td>
        <td>${row.dist || '-'}</td>
        <td>${row.vill || '-'}</td>
        <td>${row.sNo || '-'}</td>
        <td>${row.ss || '*'}</td>
        <td>${row.area ? parseFloat(row.area) : '0'}</td>
      `;
      cardTableBody.appendChild(tr);
    });
  }

  // 5. Dynamic QR Code Update
  // Create structured text for scanner (e.g. ID, Name, Mobile)
  const qrString = `AgriCard ID: ${fId}\nName: ${nameEn}\nDOB: ${formattedDob}\nMobile: ${mobile}`;
  
  const qrTarget = document.getElementById('card-qr');
  qrTarget.innerHTML = '';
  
  qrCodeGenerator = new QRCode(qrTarget, {
    text: qrString,
    width: 75,
    height: 75,
    colorDark: "#1b4332",
    colorLight: "#ffffff",
    correctLevel: QRCode.CorrectLevel.M
  });
}

/* ==========================================================================
   CRUD: SAVE / EDIT / DELETE OPERATIONS
   ========================================================================== */
async function handleFormSubmit(e) {
  e.preventDefault();

  const farmerId = document.getElementById('farmer-id').value;
  const nameEn = document.getElementById('name-en').value;
  const nameHi = document.getElementById('name-hi').value;
  const dob = document.getElementById('dob').value;
  const gender = document.getElementById('gender').value;
  const mobile = document.getElementById('mobile').value;
  const aadhaar = document.getElementById('aadhaar').value;
  const address = document.getElementById('address').value;
  
  // Photo
  const photoPreview = document.getElementById('photo-preview-img');
  const photoBase64 = photoPreview.classList.contains('hidden') ? placeholderAvatar : photoPreview.src;

  // Land Details
  const landDetails = getLandTableData();

  const cardData = {
    farmerId,
    nameEn,
    nameHi,
    dob,
    gender,
    mobile,
    aadhaar,
    address,
    photo: photoBase64,
    landDetails,
    createdAt: Date.now()
  };

  if (currentEditingId !== null) {
    cardData.id = currentEditingId;
  }

  try {
    await saveCard(cardData);
    
    alert(currentEditingId ? 'Farmer Record updated successfully!' : 'Farmer Card created and saved to local database!');
    
    resetForm();
    await loadHistory();
    switchTab('history');
  } catch (err) {
    console.error('Error saving record:', err);
    alert('Failed to save record: ' + err.message);
  }
}

async function loadHistory() {
  try {
    const list = await getAllCards();
    historyCards = list.sort((a, b) => b.createdAt - a.createdAt); // Sort newest first
    renderHistoryList(historyCards);
    updateBadges();
  } catch (err) {
    console.error('Error loading history:', err);
  }
}

function renderHistoryList(records) {
  const tbody = document.getElementById('history-list-body');
  tbody.innerHTML = '';

  if (records.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="9" class="empty-state">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-folder-open"><path d="m6 14 1.45-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.55 6a2 2 0 0 1-1.94 1.5H4a2 2 0 0 1-2-2V5c0-1.1.9-2 2-2h3.93a2 2 0 0 1 1.66.9l.82 1.2a2 2 0 0 0 1.66.9H18a2 2 0 0 1 2 2v2"/></svg>
          <p>No records found in database. Create your first card!</p>
        </td>
      </tr>
    `;
    return;
  }

  records.forEach(card => {
    // Formatting variables
    const formattedAadhaar = `XXXX XXXX ${card.aadhaar.substr(8, 4)}`;
    
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>
        <input type="checkbox" class="record-checkbox" data-id="${card.id}">
      </td>
      <td>
        <img class="table-farmer-photo" src="${card.photo || placeholderAvatar}" alt="Photo">
      </td>
      <td style="font-family: monospace; font-weight: bold;">${card.farmerId}</td>
      <td>
        <div class="farmer-table-name">${card.nameEn}</div>
        <div class="farmer-table-name-hi">${card.nameHi}</div>
      </td>
      <td>${formattedAadhaar}</td>
      <td>${card.mobile}</td>
      <td style="font-size: 0.8rem; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${card.address}">
        ${card.address}
      </td>
      <td style="text-align: center;">
        <span class="badge" style="background-color: var(--light-sage); color: var(--primary-color); font-weight: bold; border-radius: 4px;">
          ${card.landDetails ? card.landDetails.length : 0}
        </span>
      </td>
      <td>
        <div class="table-actions">
          <button class="btn btn-secondary btn-sm btn-icon edit-card-btn" data-id="${card.id}" title="Edit Card Details">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-edit-3"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
          </button>
          <button class="btn btn-primary btn-sm btn-icon print-card-btn" data-id="${card.id}" title="Print ID Card">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-printer"><path d="M6 9V2h12v7"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><path d="M6 14h12v8H6z"/></svg>
          </button>
          <button class="btn btn-secondary btn-sm btn-icon queue-card-btn" data-id="${card.id}" title="Add to Print Queue">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-file-plus"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M9 15h6"/><path d="M12 12v6"/></svg>
          </button>
          <button class="btn btn-danger btn-sm btn-icon delete-card-btn" data-id="${card.id}" title="Delete Record">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-trash-2"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/></svg>
          </button>
        </div>
      </td>
    `;

    // Attach click triggers to buttons
    tr.querySelector('.edit-card-btn').addEventListener('click', () => editCard(card.id));
    tr.querySelector('.print-card-btn').addEventListener('click', () => printSingleCardDirectly(card));
    tr.querySelector('.queue-card-btn').addEventListener('click', () => queueSingleCard(card));
    tr.querySelector('.delete-card-btn').addEventListener('click', () => deleteCardConfirm(card.id));
    
    // Checkbox state tracking
    tr.querySelector('.record-checkbox').addEventListener('change', () => {
      updateBadges();
    });

    tbody.appendChild(tr);
  });

  updateBadges();
}

function filterHistoryList() {
  const query = document.getElementById('history-search').value.toLowerCase().trim();
  
  if (query === '') {
    renderHistoryList(historyCards);
    return;
  }

  const filtered = historyCards.filter(card => {
    return (
      card.nameEn.toLowerCase().includes(query) ||
      card.nameHi.toLowerCase().includes(query) ||
      card.farmerId.toLowerCase().includes(query) ||
      card.aadhaar.includes(query) ||
      card.mobile.includes(query)
    );
  });
  
  renderHistoryList(filtered);
}

function toggleAllRecordsSelection() {
  const checkAll = document.getElementById('select-all-records').checked;
  const checkboxes = document.querySelectorAll('.record-checkbox');
  checkboxes.forEach(chk => {
    chk.checked = checkAll;
  });
  updateBadges();
}

/* ==========================================================================
   CRUD ACTIONS CALLS
   ========================================================================== */
function editCard(id) {
  const card = historyCards.find(c => c.id === id);
  if (!card) return;

  currentEditingId = card.id;

  // Fill standard fields
  document.getElementById('farmer-id').value = card.farmerId;
  document.getElementById('gender').value = card.gender;
  document.getElementById('name-en').value = card.nameEn;
  document.getElementById('name-hi').value = card.nameHi;
  document.getElementById('dob').value = card.dob;
  document.getElementById('mobile').value = card.mobile;
  document.getElementById('aadhaar').value = card.aadhaar;
  document.getElementById('address').value = card.address;

  // Handle Photo
  const previewImg = document.getElementById('photo-preview-img');
  const uploadPlaceholder = document.querySelector('.upload-placeholder');
  const removeBtn = document.querySelector('.remove-photo-btn');

  if (card.photo && card.photo !== placeholderAvatar) {
    previewImg.src = card.photo;
    previewImg.classList.remove('hidden');
    uploadPlaceholder.classList.add('hidden');
    removeBtn.classList.remove('hidden');
  } else {
    removeUploadedPhoto();
  }

  // Load Land Details Table
  const tableBody = document.querySelector('#field-details-table tbody');
  tableBody.innerHTML = '';
  
  if (card.landDetails && card.landDetails.length) {
    card.landDetails.forEach(land => {
      const distVal = land.dist || land.subDist || '';
      addLandTableRow(land.state, distVal, land.vill, land.sNo, land.ss, land.area);
    });
  } else {
    addLandTableRow();
  }

  // Switch to Creator tab and update live preview
  switchTab('creator');
  updateLivePreview();
}

async function deleteCardConfirm(id) {
  if (confirm('Are you sure you want to delete this farmer record permanently?')) {
    try {
      await deleteCardFromDB(id);
      
      // Remove from printQueue if present
      printQueue = printQueue.filter(c => c.id !== id);
      savePrintQueueToStorage();
      
      await loadHistory();
    } catch (err) {
      alert('Delete failed: ' + err.message);
    }
  }
}

async function bulkDeleteSelected() {
  const selectedCheckboxes = document.querySelectorAll('.record-checkbox:checked');
  if (selectedCheckboxes.length === 0) {
    alert('No records selected.');
    return;
  }

  if (confirm(`Are you sure you want to delete ${selectedCheckboxes.length} selected records permanently?`)) {
    try {
      for (let chk of selectedCheckboxes) {
        const id = parseInt(chk.getAttribute('data-id'));
        await deleteCardFromDB(id);
        printQueue = printQueue.filter(c => c.id !== id);
      }
      savePrintQueueToStorage();
      document.getElementById('select-all-records').checked = false;
      await loadHistory();
      alert('Selected records deleted successfully.');
    } catch (err) {
      alert('Failed to delete some records: ' + err.message);
    }
  }
}

/* ==========================================================================
   PRINT QUEUE MANAGEMENT & STORAGE
   ========================================================================== */
function loadPrintQueueFromStorage() {
  try {
    const data = localStorage.getItem('agri_print_queue');
    printQueue = data ? JSON.parse(data) : [];
  } catch (err) {
    console.error('Error loading print queue:', err);
    printQueue = [];
  }
}

function savePrintQueueToStorage() {
  try {
    localStorage.setItem('agri_print_queue', JSON.stringify(printQueue));
  } catch (err) {
    console.error('Error saving print queue:', err);
  }
}

function queueSingleCard(card) {
  if (printQueue.some(c => c.id === card.id || (c.farmerId === card.farmerId && c.id === undefined))) {
    alert('This card is already in the print queue.');
    return;
  }
  printQueue.push(card);
  savePrintQueueToStorage();
  updateBadges();
  alert('Added card to print queue.');
}

function bulkQueueSelected() {
  const selectedCheckboxes = document.querySelectorAll('.record-checkbox:checked');
  if (selectedCheckboxes.length === 0) {
    alert('No records selected.');
    return;
  }

  let addedCount = 0;
  selectedCheckboxes.forEach(chk => {
    const id = parseInt(chk.getAttribute('data-id'));
    const card = historyCards.find(c => c.id === id);
    if (card && !printQueue.some(c => c.id === card.id)) {
      printQueue.push(card);
      addedCount++;
    }
  });

  if (addedCount > 0) {
    savePrintQueueToStorage();
    updateBadges();
    // Uncheck select all
    document.getElementById('select-all-records').checked = false;
    toggleAllRecordsSelection();
    alert(`Added ${addedCount} cards to print queue.`);
  } else {
    alert('Selected cards are already in the queue.');
  }
}

function addCurrentCardToQueue() {
  // Build card representation from current form
  const farmerId = document.getElementById('farmer-id').value;
  const nameEn = document.getElementById('name-en').value || 'Sita Kumari';
  const nameHi = document.getElementById('name-hi').value || 'सीता कुमारी';
  const dob = document.getElementById('dob').value;
  const gender = document.getElementById('gender').value;
  const mobile = document.getElementById('mobile').value;
  const aadhaar = document.getElementById('aadhaar').value;
  const address = document.getElementById('address').value;
  const photoPreview = document.getElementById('photo-preview-img');
  const photo = photoPreview.classList.contains('hidden') ? placeholderAvatar : photoPreview.src;
  const landDetails = getLandTableData();

  const mockCard = {
    id: currentEditingId || undefined, // undefined if not saved yet
    farmerId,
    nameEn,
    nameHi,
    dob,
    gender,
    mobile,
    aadhaar,
    address,
    photo,
    landDetails
  };

  queueSingleCard(mockCard);
}

function renderPrintQueue() {
  const queueGrid = document.getElementById('queue-grid-list');
  queueGrid.innerHTML = '';

  if (printQueue.length === 0) {
    queueGrid.innerHTML = `
      <div class="empty-state">
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-layers"><path d="m12 3-10 9h18Z"/><path d="m22 12-10 9-10-9"/><path d="m2 17 10 9 10-9"/></svg>
        <p>Your print queue is empty. Add cards from history or the creator to print.</p>
      </div>
    `;
    return;
  }

  printQueue.forEach((card, index) => {
    const div = document.createElement('div');
    div.className = 'queue-row-card';
    
    // Formatting DOB & Aadhaar for the preview
    let formattedDob = '01/01/2060';
    if (card.dob) {
      const parts = card.dob.split('-');
      if (parts.length === 3) formattedDob = `${parts[2]}/${parts[1]}/${parts[0]}`;
    }
    
    const formattedAadhaar = card.aadhaar ? `XXXX XXXX ${card.aadhaar.substr(8, 4)}` : 'XXXX XXXX 1234';

    // Back card land details table rows HTML
    let tableRowsHtml = '';
    const previewLand = (card.landDetails || []).slice(0, 4);
    if (previewLand.length === 0) {
      tableRowsHtml = `<tr><td colspan="6" style="text-align: center; color: #aaa;">No land data added</td></tr>`;
    } else {
      previewLand.forEach(row => {
        tableRowsHtml += `
          <tr>
            <td>${row.state || '-'}</td>
            <td>${row.dist || '-'}</td>
            <td>${row.vill || '-'}</td>
            <td>${row.sNo || '-'}</td>
            <td>${row.ss || '*'}</td>
            <td>${row.area ? parseFloat(row.area) : '0'}</td>
          </tr>
        `;
      });
    }

    div.innerHTML = `
      <div class="queue-card-preview-mini">
        <!-- Front -->
        <div class="id-card-wrapper">
          <div class="id-card card-front ${selectedDesign === '2' ? 'design-2-front' : selectedDesign === '3' ? 'design-3-front' : ''}">
            <div class="leaf-decor leaf-top-right">
              <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M10 90C40 70 80 40 90 10C70 40 40 70 10 90Z" fill="#2d6a4f" opacity="0.15"/>
              </svg>
            </div>
            <div class="leaf-decor leaf-bottom-left">
              <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M90 10C60 30 20 60 10 90C30 60 60 30 90 10Z" fill="#2d6a4f" opacity="0.15"/>
              </svg>
            </div>
            <div class="card-header">
              <div class="card-logo">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="leaf-svg"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 3.58-1 8a7 7 0 0 1-7 10Z"/><path d="M9 22v-4h4v4"/><path d="M11 15h0"/></svg>
                <div class="card-logo-text"><span class="agri">Ägri</span><span class="card-text">Cård</span></div>
              </div>
              <div class="card-title-main"></div>
            </div>
            <div class="card-body">
              <div class="photo-container">
                <img src="${card.photo || placeholderAvatar}" alt="Photo">
              </div>
              <div class="farmer-details">
                <div class="detail-name">${card.nameEn}</div>
                <div class="detail-name-hi">${card.nameHi}</div>
                <div class="detail-grid">
                  <div class="detail-label">DOB:</div>
                  <div class="detail-val">${formattedDob}</div>
                  <div class="detail-label">Gender:</div>
                  <div class="detail-val">${card.gender}</div>
                  <div class="detail-label">Mobile:</div>
                  <div class="detail-val">${card.mobile}</div>
                  ${card.aadhaar ? `
                    <div class="detail-label">Aadhaar:</div>
                    <div class="detail-val">${formattedAadhaar}</div>
                  ` : ''}
                </div>
              </div>
              <div class="qr-container">
                <div class="qr-code" id="queue-qr-front-${index}"></div>
              </div>
            </div>
            <div class="id-badge-container">
              <div class="farmer-id-badge">Farmer Id: <span>${card.farmerId}</span></div>
            </div>
            <div class="card-footer">
        <span class="disclaimer">This card is strictly for personal use and does not constitute a government-issued identification.</span>
              <span class="footer-hi">FARMER ID</span>
            </div>
          </div>
        </div>

        <!-- Back -->
        <div class="id-card-wrapper">
          <div class="id-card card-back ${selectedDesign === '2' ? 'design-2-back' : selectedDesign === '3' ? 'design-3-back' : ''}">
            <div class="leaf-decor leaf-top-right">
              <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M10 90C40 70 80 40 90 10C70 40 40 70 10 90Z" fill="#2d6a4f" opacity="0.15"/>
              </svg>
            </div>
            <div class="leaf-decor leaf-bottom-left">
              <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M90 10C60 30 20 60 10 90C30 60 60 30 90 10Z" fill="#2d6a4f" opacity="0.15"/>
              </svg>
            </div>
            <div class="card-header">
              <div class="card-logo">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="leaf-svg"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 3.58-1 8a7 7 0 0 1-7 10Z"/><path d="M9 22v-4h4v4"/><path d="M11 15h0"/></svg>
                <div class="card-logo-text"><span class="agri">Ägri</span><span class="card-text">Cård</span></div>
              </div>
            </div>
            <div class="card-back-body">
              <div class="address-container">
                <strong>Add:</strong> <span>${card.address}</span>
              </div>
              <div class="field-table-container">
                <table class="card-field-table">
                  <thead>
                    <tr>
                      <th>State</th>
                      <th>Dist</th>
                      <th>Vill</th>
                      <th>S.No</th>
                      <th>S/S</th>
                      <th>Area</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${tableRowsHtml}
                  </tbody>
                </table>
              </div>
            </div>
            <div class="card-footer">
        <span class="disclaimer">This card is strictly for personal use and does not constitute a government-issued identification.</span>
              <span class="footer-hi">FARMER ID</span>
            </div>
          </div>
        </div>
      </div>

      <div class="queue-card-info">
        <h4>${card.nameEn}</h4>
        <p>ID: ${card.farmerId} | Aadhaar: ${formattedAadhaar}</p>
        <p>Mobile: ${card.mobile}</p>
      </div>

      <div class="queue-actions">
        <button class="btn btn-danger btn-sm" onclick="removeCardFromQueueByIndex(${index})">
          <i data-lucide="trash-2" style="width: 14px; height: 14px;"></i> Remove
        </button>
      </div>
    `;

    queueGrid.appendChild(div);

    // Initialize QR Code inside the mini card preview asynchronously
    setTimeout(() => {
      const qrString = `AgriCard ID: ${card.farmerId}\nName: ${card.nameEn}\nDOB: ${formattedDob}\nMobile: ${card.mobile}`;
      const el = document.getElementById(`queue-qr-front-${index}`);
      if (el) {
        new QRCode(el, {
          text: qrString,
          width: 75,
          height: 75,
          colorDark: "#1b4332",
          colorLight: "#ffffff",
          correctLevel: QRCode.CorrectLevel.M
        });
      }
    }, 50);
  });

  if (typeof lucide !== 'undefined') {
    lucide.createIcons({ attrs: { class: 'lucide' } });
  }
}

// Global scope window triggers for onclick handlers in list rendering
window.removeCardFromQueueByIndex = function(index) {
  printQueue.splice(index, 1);
  savePrintQueueToStorage();
  renderPrintQueue();
  updateBadges();
};

/* ==========================================================================
   PRINT ENGINE (SINGLE & BATCH A4 COPIES)
   ========================================================================== */


function printSingleCardDirectly(cardData) {
  // If invoked with no argument, read from active form
  let card = cardData;
  if (!card || card instanceof Event) {
    const farmerId = document.getElementById('farmer-id').value;
    const nameEn = document.getElementById('name-en').value || 'Sita Kumari';
    const nameHi = document.getElementById('name-hi').value || 'सीता कुमारी';
    const dob = document.getElementById('dob').value;
    const gender = document.getElementById('gender').value;
    const mobile = document.getElementById('mobile').value;
    const aadhaar = document.getElementById('aadhaar').value;
    const address = document.getElementById('address').value;
    const photoPreview = document.getElementById('photo-preview-img');
    const photo = photoPreview.classList.contains('hidden') ? placeholderAvatar : photoPreview.src;
    const landDetails = getLandTableData();

    card = {
      farmerId,
      nameEn,
      nameHi,
      dob,
      gender,
      mobile,
      aadhaar,
      address,
      photo,
      landDetails
    };
  }

  const printContainer = document.getElementById('print-container');
  printContainer.innerHTML = '';

  const printPageDiv = document.createElement('div');
  printPageDiv.className = 'print-page';

  const row = createCardPrintRowHTML(card, 0);
  printPageDiv.appendChild(row);
  printContainer.appendChild(printPageDiv);

  // Generate QR Code inside hidden div
  setTimeout(() => {
    generatePrintQR(card, 0);
    chargeWallet('farmer-id', 1).then(() => {
        window.print();
    }).catch(err => {
        alert('Wallet Error: ' + err.message);
        if (err.isInsufficientBalance) {
            window.location.href = err.redirectUrl || '/wallet/topup/';
        }
    });
  }, 150);
}

function printQueueA4Layout() {
  if (printQueue.length === 0) {
    alert('The print queue is empty! Add cards to the queue first.');
    return;
  }

  const printContainer = document.getElementById('print-container');
  printContainer.innerHTML = '';

  // Get User setting for cards per A4 page
  const cardsPerPageSelect = document.getElementById('cards-per-page');
  const cardsPerPage = parseInt(cardsPerPageSelect.value || '3');

  let currentPrintPage = null;
  
  printQueue.forEach((card, index) => {
    // Group cards into A4 pages based on user preference
    if (index % cardsPerPage === 0) {
      currentPrintPage = document.createElement('div');
      currentPrintPage.className = 'print-page';
      printContainer.appendChild(currentPrintPage);
    }

    const row = createCardPrintRowHTML(card, index);
    currentPrintPage.appendChild(row);
  });

  const btn = document.getElementById('trigger-batch-print');
  if(btn) { btn.disabled = true; btn.innerHTML = '<i data-lucide="loader"></i> Charging...'; lucide.createIcons(); }
  
  chargeWallet('farmer-id', printQueue.length).then(() => {
      if(btn) { btn.disabled = false; btn.innerHTML = '<i data-lucide="printer"></i> Print Queue Now (A4 Layout)'; lucide.createIcons(); }
      // Generate QR codes for all print cards sequentially
      setTimeout(() => {
        printQueue.forEach((card, index) => {
          generatePrintQR(card, index);
        });
        window.print();
      }, 200);
  }).catch(err => {
      if(btn) { btn.disabled = false; btn.innerHTML = '<i data-lucide="printer"></i> Print Queue Now (A4 Layout)'; lucide.createIcons(); }
      alert('Wallet Error: ' + err.message);
      if (err.isInsufficientBalance) {
          window.location.href = err.redirectUrl || '/wallet/topup/';
      }
  });
}

/* ==========================================================================
   DOM GENERATION HELPERS FOR PRINT ENGINE
   ========================================================================== */
function createCardPrintRowHTML(card, index) {
  // Format details for high-fidelity output
  let formattedDob = '01/01/2060';
  if (card.dob) {
    const parts = card.dob.split('-');
    if (parts.length === 3) formattedDob = `${parts[2]}/${parts[1]}/${parts[0]}`;
  }
  
  const formattedAadhaar = card.aadhaar && card.aadhaar.length === 12 
    ? `XXXX XXXX ${card.aadhaar.substr(8, 4)}` 
    : card.aadhaar || 'XXXX XXXX 1234';

  let tableRowsHtml = '';
  const previewLand = (card.landDetails || []).slice(0, 4);
  if (previewLand.length === 0) {
    tableRowsHtml = `<tr><td colspan="6" style="text-align: center; color: #aaa; font-size: 5.5pt;">No land data</td></tr>`;
  } else {
    previewLand.forEach(row => {
      tableRowsHtml += `
        <tr>
          <td>${row.state || '-'}</td>
          <td>${row.dist || '-'}</td>
          <td>${row.vill || '-'}</td>
          <td>${row.sNo || '-'}</td>
          <td>${row.ss || '*'}</td>
          <td>${row.area ? parseFloat(row.area) : '0'}</td>
        </tr>
      `;
    });
  }

  const rowDiv = document.createElement('div');
  rowDiv.className = 'print-row-item';
  rowDiv.innerHTML = `
    <!-- FRONT OF CARD -->
    <div class="id-card card-front ${selectedDesign === '2' ? 'design-2-front' : selectedDesign === '3' ? 'design-3-front' : ''}">
      <div class="leaf-decor leaf-top-right">
        <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M10 90C40 70 80 40 90 10C70 40 40 70 10 90Z" fill="#2d6a4f" />
        </svg>
      </div>
      <div class="leaf-decor leaf-bottom-left">
        <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M90 10C60 30 20 60 10 90C30 60 60 30 90 10Z" fill="#2d6a4f" />
        </svg>
      </div>
      <div class="card-header">
        <div class="card-logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="leaf-svg"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 3.58-1 8a7 7 0 0 1-7 10Z"/><path d="M9 22v-4h4v4"/><path d="M11 15h0"/></svg>
          <div class="card-logo-text"><span class="agri">Ägri</span><span class="card-text">Cård</span></div>
        </div>
        <div class="card-title-main"></div>
      </div>
      <div class="card-body">
        <div class="photo-container">
          <img src="${card.photo || placeholderAvatar}" alt="Photo">
        </div>
        <div class="farmer-details">
          <div class="detail-name">${card.nameEn}</div>
          <div class="detail-name-hi">${card.nameHi}</div>
          <div class="detail-grid">
            <div class="detail-label">DOB:</div>
            <div class="detail-val">${formattedDob}</div>
            <div class="detail-label">Gender:</div>
            <div class="detail-val">${card.gender}</div>
            <div class="detail-label">Mobile:</div>
            <div class="detail-val">${card.mobile}</div>
            ${card.aadhaar ? `
              <div class="detail-label">Aadhaar:</div>
              <div class="detail-val">${formattedAadhaar}</div>
            ` : ''}
          </div>
        </div>
        <div class="qr-container">
          <div class="qr-code" id="print-qr-front-${index}"></div>
        </div>
      </div>
      <div class="id-badge-container">
        <div class="farmer-id-badge">Farmer Id: <span>${card.farmerId}</span></div>
      </div>
      <div class="card-footer">
        <span class="disclaimer">This card is strictly for personal use and does not constitute a government-issued identification.</span>
        <span class="footer-hi">FARMER ID</span>
      </div>
    </div>

    <!-- BACK OF CARD -->
    <div class="id-card card-back ${selectedDesign === '2' ? 'design-2-back' : selectedDesign === '3' ? 'design-3-back' : ''}">
      <div class="leaf-decor leaf-top-right">
        <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M10 90C40 70 80 40 90 10C70 40 40 70 10 90Z" fill="#2d6a4f" />
        </svg>
      </div>
      <div class="leaf-decor leaf-bottom-left">
        <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M90 10C60 30 20 60 10 90C30 60 60 30 90 10Z" fill="#2d6a4f" />
        </svg>
      </div>
      <div class="card-header">
        <div class="card-logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="leaf-svg"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 3.58-1 8a7 7 0 0 1-7 10Z"/><path d="M9 22v-4h4v4"/><path d="M11 15h0"/></svg>
          <div class="card-logo-text"><span class="agri">Ägri</span><span class="card-text">Cård</span></div>
        </div>
      </div>
      <div class="card-back-body">
        <div class="address-container">
          <strong>Add:</strong> <span>${card.address}</span>
        </div>
        <div class="field-table-container">
          <table class="card-field-table">
            <thead>
              <tr>
                <th>State</th>
                <th>Dist</th>
                <th>Vill</th>
                <th>S.No</th>
                <th>S/S</th>
                <th>Area</th>
              </tr>
            </thead>
            <tbody>
              ${tableRowsHtml}
            </tbody>
          </table>
        </div>
      </div>
      <div class="card-footer">
        <span class="disclaimer">This card is strictly for personal use and does not constitute a government-issued identification.</span>
        <span class="footer-hi">FARMER ID</span>
      </div>
    </div>
  `;
  
  return rowDiv;
}

function generatePrintQR(card, index) {
  let formattedDob = '01/01/2060';
  if (card.dob) {
    const parts = card.dob.split('-');
    if (parts.length === 3) formattedDob = `${parts[2]}/${parts[1]}/${parts[0]}`;
  }
  const qrString = `AgriCard ID: ${card.farmerId}\nName: ${card.nameEn}\nDOB: ${formattedDob}\nMobile: ${card.mobile}`;
  
  const el = document.getElementById(`print-qr-front-${index}`);
  if (el) {
    new QRCode(el, {
      text: qrString,
      width: 65, // slightly smaller width to match high-density print size in mm
      height: 65,
      colorDark: "#1b4332",
      colorLight: "#ffffff",
      correctLevel: QRCode.CorrectLevel.M
    });
  }
}

/* ==========================================================================
   PDF SCANNING AND AUTOMATIC SCAN & FILL SYSTEM
   ========================================================================== */
async function handlePdfFileSelect() {
  const pdfInput = document.getElementById('pdf-upload');
  if (!pdfInput || !pdfInput.files || !pdfInput.files[0]) return;
  const file = pdfInput.files[0];
  
  const placeholder = document.getElementById('pdf-upload-placeholder');
  const progress = document.getElementById('pdf-upload-progress');
  const success = document.getElementById('pdf-upload-success');
  const error = document.getElementById('pdf-upload-error');
  
  // Show progress state
  placeholder.classList.add('hidden');
  progress.classList.remove('hidden');
  success.classList.add('hidden');
  error.classList.add('hidden');
  
  try {
    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        const arrayBuffer = e.target.result;
        const result = await extractTextAndPhotoFromPdf(arrayBuffer);
        
        // Auto-fill form fields
        fillFormFromParsedData(result);
        
        // Show success state
        progress.classList.add('hidden');
        success.classList.remove('hidden');
        
        // Reset file input
        pdfInput.value = '';
        
        // Clear success message after 4 seconds
        setTimeout(() => {
          success.classList.add('hidden');
          placeholder.classList.remove('hidden');
        }, 4000);
      } catch (err) {
        console.error("Error processing PDF contents:", err);
        showPdfScanError(err.message || "Failed to scan details from this PDF document.");
      }
    };
    reader.onerror = () => {
      showPdfScanError("Failed to read PDF file.");
    };
    reader.readAsArrayBuffer(file);
  } catch (err) {
    console.error("FileReader failed:", err);
    showPdfScanError("FileReader failed.");
  }
}

function showPdfScanError(message) {
  const placeholder = document.getElementById('pdf-upload-placeholder');
  const progress = document.getElementById('pdf-upload-progress');
  const error = document.getElementById('pdf-upload-error');
  const errMessage = document.getElementById('pdf-error-message');
  
  progress.classList.add('hidden');
  error.classList.remove('hidden');
  if (errMessage) errMessage.innerText = message;
  
  setTimeout(() => {
    error.classList.add('hidden');
    placeholder.classList.remove('hidden');
  }, 4000);
}

async function extractTextAndPhotoFromPdf(arrayBuffer) {
  if (typeof pdfjsLib === 'undefined') {
    throw new Error("PDF.js library is not loaded. Please check your internet connection.");
  }
  
  // Initialize worker
  pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.worker.min.js';
  
  const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
  const pdf = await loadingTask.promise;
  
  let extractedText = "";
  let photoDataUrl = null;
  
  // Extract Text from all pages
  for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
    const page = await pdf.getPage(pageNum);
    const textContent = await page.getTextContent();
    
    let pageText = "";
    if (pageNum === 1) {
      // Use layout-aware text joining to combine inline fragments on page 1 (such as Hindi names)
      pageText = parseTextContentLayout(textContent);
    } else {
      // Use simple new-line joining for pages 2 & 3 to keep table row parsing intact
      pageText = textContent.items.map(item => item.str).join("\n");
    }
    
    extractedText += `\n--- Page ${pageNum} Text ---\n` + pageText;
    
    // Page 1: Extract Embedded Photo
    if (pageNum === 1) {
      photoDataUrl = await extractPhotoFromPage(page);
    }
  }
  
  return {
    text: extractedText,
    photo: photoDataUrl
  };
}

function parseTextContentLayout(textContent) {
  const tolerance = 0.5; // Tighter tolerance to prevent chaining lines
  const lines = [];
  
  // Sort items by Y descending first (top to bottom)
  const sortedItems = [...textContent.items]
    .filter(item => item.str && item.str.trim() !== '')
    .sort((a, b) => b.transform[5] - a.transform[5]);
    
  sortedItems.forEach(item => {
    const y = item.transform[5];
    let foundLine = lines.find(line => Math.abs(line.y - y) <= tolerance);
    if (!foundLine) {
      foundLine = { y: y, items: [] };
      lines.push(foundLine);
    }
    foundLine.items.push(item);
  });
  
  const textLines = [];
  
  lines.forEach(line => {
    // Sort items on the same line horizontally (left to right)
    line.items.sort((a, b) => a.transform[4] - b.transform[4]);
    
    let currentLineText = "";
    let lastXEnd = -1;
    
    line.items.forEach(item => {
      const x = item.transform[4];
      const itemWidth = item.width || (item.str.length * 6); // estimate width if not provided
      
      if (lastXEnd !== -1) {
        const gap = x - lastXEnd;
        // If horizontal gap is large, treat as a different column (split onto a new line)
        if (gap > 40.0) {
          textLines.push(currentLineText);
          currentLineText = item.str;
          lastXEnd = x + itemWidth;
          return;
        }
      }
      
      if (currentLineText === "") {
        currentLineText = item.str;
      } else {
        const needsSpace = !currentLineText.endsWith(" ") && !item.str.startsWith(" ");
        currentLineText += (needsSpace ? " " : "") + item.str;
      }
      lastXEnd = x + itemWidth;
    });
    
    if (currentLineText !== "") {
      textLines.push(currentLineText);
    }
  });
  
  return textLines.join("\n");
}

async function extractPhotoFromPage(page) {
  try {
    const operatorList = await page.getOperatorList();
    for (let i = 0; i < operatorList.fnArray.length; i++) {
      const fn = operatorList.fnArray[i];
      // Search for image paint operators
      if (fn === pdfjsLib.OPS.paintImageXObject || fn === pdfjsLib.OPS.paintJpegXObject) {
        const imgKey = operatorList.argsArray[i][0];
        const imgObj = await getImageFromObjs(page, imgKey);
        
        if (imgObj && imgObj.width && imgObj.height && imgObj.data) {
          const dataUrl = convertPdfImageToDataUrl(imgObj);
          if (dataUrl) return dataUrl;
        }
      }
    }
  } catch (err) {
    console.error("Failed to extract photo from operator list:", err);
  }
  return null;
}

function getImageFromObjs(page, imgKey) {
  return new Promise((resolve) => {
    try {
      const img = page.objs.get(imgKey);
      if (img && img.width && img.height && img.data) {
        resolve(img);
        return;
      }
    } catch (e) {}

    try {
      page.objs.get(imgKey, (img) => {
        if (img) {
          resolve(img);
        } else {
          resolve(null);
        }
      });
      return;
    } catch (e) {}

    try {
      const img = page.commonObjs.get(imgKey);
      if (img && img.width && img.height && img.data) {
        resolve(img);
        return;
      }
    } catch (e) {}

    try {
      page.commonObjs.get(imgKey, (img) => {
        resolve(img || null);
      });
      return;
    } catch (e) {}

    resolve(null);
  });
}

function convertPdfImageToDataUrl(pdfImageObj) {
  const canvas = document.createElement('canvas');
  canvas.width = pdfImageObj.width;
  canvas.height = pdfImageObj.height;
  const ctx = canvas.getContext('2d');
  
  const numPixels = pdfImageObj.width * pdfImageObj.height;
  const imgData = ctx.createImageData(pdfImageObj.width, pdfImageObj.height);
  const data = imgData.data;
  const rawData = pdfImageObj.data;
  
  if (rawData.length === numPixels * 3) {
    // RGB
    let srcIdx = 0;
    let destIdx = 0;
    for (let i = 0; i < numPixels; i++) {
      data[destIdx] = rawData[srcIdx];       // R
      data[destIdx + 1] = rawData[srcIdx + 1]; // G
      data[destIdx + 2] = rawData[srcIdx + 2]; // B
      data[destIdx + 3] = 255;                 // A
      srcIdx += 3;
      destIdx += 4;
    }
  } else if (rawData.length === numPixels * 4) {
    // RGBA
    data.set(rawData);
  } else if (rawData.length === numPixels) {
    // Grayscale
    let destIdx = 0;
    for (let i = 0; i < numPixels; i++) {
      const val = rawData[i];
      data[destIdx] = val;
      data[destIdx + 1] = val;
      data[destIdx + 2] = val;
      data[destIdx + 3] = 255;
      destIdx += 4;
    }
  } else {
    // Fallback just in case
    let srcIdx = 0;
    let destIdx = 0;
    for (let i = 0; i < numPixels; i++) {
      if (srcIdx < rawData.length) {
        data[destIdx] = rawData[srcIdx];
        data[destIdx + 1] = rawData[srcIdx + 1] !== undefined ? rawData[srcIdx + 1] : rawData[srcIdx];
        data[destIdx + 2] = rawData[srcIdx + 2] !== undefined ? rawData[srcIdx + 2] : rawData[srcIdx];
        data[destIdx + 3] = 255;
      }
      srcIdx += (rawData.length === numPixels * 3) ? 3 : 4;
      destIdx += 4;
    }
  }
  
  ctx.putImageData(imgData, 0, 0);
  
  // Crop / resize if necessary (keep size small and compact for Base64 storage)
  const maxDim = 300;
  if (canvas.width > maxDim || canvas.height > maxDim) {
    const scaleCanvas = document.createElement('canvas');
    let w = canvas.width;
    let h = canvas.height;
    if (w > h) {
      h = Math.round((h * maxDim) / w);
      w = maxDim;
    } else {
      w = Math.round((w * maxDim) / h);
      h = maxDim;
    }
    scaleCanvas.width = w;
    scaleCanvas.height = h;
    const scaleCtx = scaleCanvas.getContext('2d');
    scaleCtx.drawImage(canvas, 0, 0, w, h);
    return scaleCanvas.toDataURL('image/jpeg', 0.85);
  }
  
  return canvas.toDataURL('image/jpeg', 0.85);
}

function fillFormFromParsedData(result) {
  const text = result.text;
  const photo = result.photo;
  
  // 1. Farmer ID / Enrollment number
  let enrollmentNo = "";
  const enrollMatch = text.match(/Farmer enrollment number:\s*\n*([\d_]+)/i);
  if (enrollMatch && enrollMatch[1]) {
    enrollmentNo = enrollMatch[1].trim();
  }
  
  let farmerIdVal = "";
  if (enrollmentNo) {
    const cleanDigits = enrollmentNo.replace(/_/g, "");
    if (cleanDigits.length >= 10) {
      farmerIdVal = cleanDigits.substring(1, 10);
    } else {
      farmerIdVal = cleanDigits.substring(0, 9);
    }
  } else {
    farmerIdVal = generateFarmerId();
  }

  // 2. English Name
  let nameEn = "";
  const nameEnMatch = text.match(/Farmer Name as per Aadhaar in English\s*([^\n]+)/i);
  if (nameEnMatch && nameEnMatch[1]) {
    nameEn = nameEnMatch[1].trim();
  }

  // 3. Local Name
  let nameHi = "";
  const nameHiMatch = text.match(/Farmer(?:’|')s Name in Local Language\s*([^\n]+)/i);
  if (nameHiMatch && nameHiMatch[1]) {
    nameHi = nameHiMatch[1].trim();
  }

  // 4. Gender
  let gender = "Male";
  const genderMatch = text.match(/Gender\s*(Male|Female|Other)/i);
  if (genderMatch && genderMatch[1]) {
    gender = genderMatch[1].trim();
    gender = gender.charAt(0).toUpperCase() + gender.slice(1).toLowerCase();
  }

  // 5. Date of Birth
  let dobFormatted = "";
  const dobMatch = text.match(/Date of Birth\s*(\d{2})\/(\d{2})\/(\d{2,4})/i);
  if (dobMatch) {
    const day = dobMatch[1];
    const month = dobMatch[2];
    let year = dobMatch[3];
    if (year.length === 2) {
      const currentYear = new Date().getFullYear() % 100;
      const yrInt = parseInt(year);
      if (yrInt > currentYear) {
        year = "19" + year;
      } else {
        year = "20" + year;
      }
    }
    dobFormatted = `${year}-${month}-${day}`;
  }

  // 6. Mobile Number
  let mobile = "";
  const mobileMatch = text.match(/Mobile Number\s*(\d{10})/i);
  if (mobileMatch && mobileMatch[1]) {
    mobile = mobileMatch[1].trim();
  }

  // 7. Address
  let addressEn = "";
  const addressMatch = text.match(/Address In English\s*([^\n]+)/i);
  if (addressMatch && addressMatch[1]) {
    addressEn = addressMatch[1].trim();
  }

  // 8. Land Details parsing
  const parsedLand = parseLandDetailsFromText(text);

  // Apply to Form Fields
  if (farmerIdVal) document.getElementById('farmer-id').value = farmerIdVal;
  if (nameEn) document.getElementById('name-en').value = nameEn;
  if (nameHi) document.getElementById('name-hi').value = nameHi;
  if (gender) document.getElementById('gender').value = gender;
  if (dobFormatted) document.getElementById('dob').value = dobFormatted;
  if (mobile) document.getElementById('mobile').value = mobile;
  if (addressEn) document.getElementById('address').value = addressEn;

  // Clear Aadhaar field since it is not in the PDF (so user can fill it)
  document.getElementById('aadhaar').value = "";

  // Apply Photo
  if (photo) {
    const previewImg = document.getElementById('photo-preview-img');
    const uploadPlaceholder = document.querySelector('.upload-placeholder');
    const removeBtn = document.querySelector('.remove-photo-btn');
    
    previewImg.src = photo;
    previewImg.classList.remove('hidden');
    uploadPlaceholder.classList.add('hidden');
    removeBtn.classList.remove('hidden');
    
    document.getElementById('card-photo').src = photo;
  } else {
    removeUploadedPhoto();
  }

  // Populate Land Details Table
  const tableBody = document.querySelector('#field-details-table tbody');
  tableBody.innerHTML = '';
  
  if (parsedLand && parsedLand.length > 0) {
    parsedLand.forEach(land => {
      addLandTableRow(land.state, land.dist, land.vill, land.sNo, land.ss, land.area);
    });
  } else {
    addLandTableRow();
  }

  // Trigger preview update
  updateLivePreview();
}

function parseLandDetailsFromText(text) {
  const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 0);
  const rows = [];
  
  let currentTokens = [];
  let isParsingTable = false;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    
    const isStateStart = (line.toUpperCase() === "UTTAR" && lines[i+1] && lines[i+1].toUpperCase() === "PRADESH") || 
                         (line.toUpperCase() === "UTTAR PRADESH");
                         
    if (isStateStart) {
      if (currentTokens.length > 0) {
        rows.push(currentTokens);
        currentTokens = [];
      }
      isParsingTable = true;
      currentTokens.push("UTTAR PRADESH");
      if (line.toUpperCase() === "UTTAR") {
        i++; // skip next since combined
      }
      continue;
    }
    
    if (line.toUpperCase() === "ANNEXURE" || line.includes("CONSENT")) {
      if (currentTokens.length > 0) {
        rows.push(currentTokens);
        currentTokens = [];
      }
      isParsingTable = false;
    }
    
    if (isParsingTable) {
      currentTokens.push(line);
    }
  }
  
  if (currentTokens.length > 0) {
    rows.push(currentTokens);
  }
  
  const parsedRows = [];
  rows.forEach(tokens => {
    const merged = mergeFragmentedWords(tokens);
    if (merged.length < 5) return;
    
    const state = merged[0];
    
    let sNoIdx = -1;
    for (let j = 1; j < merged.length; j++) {
      if (/^\d+$/.test(merged[j]) && parseInt(merged[j]) < 10000) {
        sNoIdx = j;
        break;
      }
    }
    
    if (sNoIdx === -1) return;
    
    const sNo = merged[sNoIdx];
    
    const dist = merged[1];
    
    // Village is everything between District (index 1) and S.No (index sNoIdx)
    let villageParts = [];
    for (let j = 2; j < sNoIdx; j++) {
      villageParts.push(merged[j]);
    }
    const vill = villageParts.join(", ") || "Madhwapur Kalan";
    
    let ss = "*";
    // Check if there is a fraction first
    for (let j = sNoIdx + 1; j < merged.length; j++) {
      if (/\d+\/\d+/.test(merged[j])) {
        ss = merged[j];
        break;
      }
    }
    // If no fraction, look for Whole / Joint / Single
    if (ss === "*") {
      for (let j = sNoIdx + 1; j < merged.length; j++) {
        const token = merged[j];
        if (/Whole/i.test(token)) {
          ss = token;
          break;
        } else if (/Joint/i.test(token)) {
          ss = token;
          break;
        } else if (/Single/i.test(token)) {
          ss = token;
        }
      }
    }
    
    let area = "0.000000";
    for (let j = merged.length - 1; j > sNoIdx; j--) {
      const cleanToken = merged[j].replace(/,/g, "").trim();
      if (/^\d+\.\d+$/.test(cleanToken)) {
        area = parseFloat(cleanToken).toFixed(6);
        break;
      }
    }
    
    parsedRows.push({
      state: state.toUpperCase(),
      dist: dist.toUpperCase(),
      vill: vill,
      sNo: sNo,
      ss: ss,
      area: area
    });
  });
  
  return parsedRows;
}

function mergeFragmentedWords(tokens) {
  const merged = [];
  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i];
    if (merged.length > 0 && (token.startsWith('ur') || token.startsWith('nagar') || /^[a-z]/.test(token))) {
      merged[merged.length - 1] = merged[merged.length - 1] + (token.startsWith('ur') ? '' : ' ') + token;
    } else {
      merged.push(token);
    }
  }
  return merged;
}
