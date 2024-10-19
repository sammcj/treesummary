// @ts-nocheck
// This file is plain JavaScript. TypeScript checking is disabled to avoid false positives.

document.addEventListener('DOMContentLoaded', () => {
  const fileTree = document.getElementById('file-tree');
  const bucketContainer = document.getElementById('bucket-container');
  const newBucketBtn = document.getElementById('new-bucket-btn');
  const settingsBtn = document.getElementById('settings-btn');
  const settingsModal = document.getElementById('settings-modal');
  const settingsForm = document.getElementById('settings-form');
  const closeSettingsBtn = document.getElementById('close-settings');
  const analysisResults = document.getElementById('analysis-results');

  let settings = loadSettings();

  // Mock file system for demonstration
  const fileSystem = {
    'project': {
      'src': {
        'components': {
          'Header.js': null,
          'Footer.js': null
        },
        'pages': {
          'Home.js': null,
          'About.js': null
        },
        'App.js': null
      },
      'public': {
        'index.html': null,
        'styles.css': null
      },
      'package.json': null,
      'README.md': null
    }
  };

  if (fileTree) renderFileTree(fileTree, fileSystem);

  if (newBucketBtn) newBucketBtn.addEventListener('click', createNewBucket);
  if (settingsBtn && settingsModal) settingsBtn.addEventListener('click', () => settingsModal.style.display = 'block');
  if (closeSettingsBtn && settingsModal) closeSettingsBtn.addEventListener('click', () => settingsModal.style.display = 'none');
  if (settingsForm) settingsForm.addEventListener('submit', saveSettings);

  function renderFileTree(container, structure, path = '') {
    for (const [name, content] of Object.entries(structure)) {
      const item = document.createElement('div');
      const fullPath = path ? `${path}/${name}` : name;

      if (content === null) {
        item.className = 'file-item';
        item.textContent = name;
        item.draggable = true;
        item.dataset.path = fullPath;
        item.addEventListener('dragstart', onDragStart);
      } else {
        item.className = 'folder-item';
        item.textContent = name;
        const subContainer = document.createElement('div');
        subContainer.style.paddingLeft = '20px';
        renderFileTree(subContainer, content, fullPath);
        item.appendChild(subContainer);
      }

          container.appendChild(item);
        }
    }

  function onDragStart(event) {
    if (event.dataTransfer && event.target && event.target.dataset) {
      event.dataTransfer.setData('text/plain', event.target.dataset.path || '');
    }
  }

  function createNewBucket() {
    if (!bucketContainer) return;
    const bucket = document.createElement('div');
    bucket.className = 'bucket';
    bucket.innerHTML = '<h3>New Bucket</h3><ul></ul>';
    bucket.addEventListener('dragover', onDragOver);
    bucket.addEventListener('drop', onDrop);
    bucketContainer.appendChild(bucket);
  }

  function onDragOver(event) {
    event.preventDefault();
  }

  function onDrop(event) {
    event.preventDefault();
    if (!event.dataTransfer) return;
    const path = event.dataTransfer.getData('text');
    const item = document.createElement('li');
    item.textContent = path;
    const removeBtn = document.createElement('button');
    removeBtn.textContent = 'Remove';
    removeBtn.addEventListener('click', () => item.remove());
    item.appendChild(removeBtn);
    const ul = event.target.querySelector('ul');
    if (ul) ul.appendChild(item);
  }

  function loadSettings() {
    const savedSettings = localStorage.getItem('analyzerSettings');
    return savedSettings ? JSON.parse(savedSettings) : {
      fileExtensions: 'js,py,html,css',
      ignorePaths: 'node_modules,dist',
      supersummaryInterval: 10,
      generateFinalSummary: true,
      generateModernisationSummary: true
    };
  }

  function saveSettings(event) {
    event.preventDefault();
    const fileExtensionsInput = document.getElementById('file-extensions');
    const ignorePathsInput = document.getElementById('ignore-paths');
    const supersummaryIntervalInput = document.getElementById('supersummary-interval');
    const generateFinalSummaryInput = document.getElementById('generate-final-summary');
    const generateModernisationSummaryInput = document.getElementById('generate-modernisation-summary');

    settings = {
      fileExtensions: fileExtensionsInput ? fileExtensionsInput.value || '' : '',
      ignorePaths: ignorePathsInput ? ignorePathsInput.value || '' : '',
      supersummaryInterval: supersummaryIntervalInput ? parseInt(supersummaryIntervalInput.value || '10') : 10,
      generateFinalSummary: generateFinalSummaryInput ? generateFinalSummaryInput.checked : false,
      generateModernisationSummary: generateModernisationSummaryInput ? generateModernisationSummaryInput.checked : false
    };
    localStorage.setItem('analyzerSettings', JSON.stringify(settings));
    if (settingsModal) settingsModal.style.display = 'none';
  }

  function analyzeProject() {
    if (!bucketContainer) return;
    const buckets = Array.from(bucketContainer.children).map(bucket => {
      const bucketName = bucket.querySelector('h3');
      return {
        name: bucketName ? bucketName.textContent : 'Unnamed Bucket',
        files: Array.from(bucket.querySelectorAll('li')).map(li => li.textContent || '')
      };
        });

      fetch('http://localhost:5000/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ buckets, settings }),
      })
        .then(response => response.json())
        .then(data => displayResults(data))
        .catch(error => console.error('Error:', error));
    }

  function displayResults(data) {
    if (!analysisResults || !data) return;
    analysisResults.style.display = 'block';
    const resultsContainer = document.getElementById('results-container');
    if (!resultsContainer) return;
    resultsContainer.innerHTML = '';

    for (const bucket of data.buckets) {
      const bucketDiv = document.createElement('div');
      bucketDiv.innerHTML = `<h3>${bucket.name}</h3>`;

      for (const [file, summary] of Object.entries(bucket.summaries)) {
        bucketDiv.innerHTML += `
                    <h4>${file}</h4>
                    <p>${summary.summary}</p>
                    ${summary.modernisation_recommendations ? `<h5>Modernisation Recommendations</h5><p>${summary.modernisation_recommendations}</p>` : ''}
                `;
      }

          if (bucket.supersummary) {
            bucketDiv.innerHTML += `<h4>Bucket Supersummary</h4><p>${bucket.supersummary}</p>`;
            }

          resultsContainer.appendChild(bucketDiv);
        }

      if (data.final_summary) {
        resultsContainer.innerHTML += `<h3>Final Summary</h3><p>${data.final_summary}</p>`;
        }

      if (data.modernisation_summary) {
        resultsContainer.innerHTML += `<h3>Modernisation Summary</h3><p>${data.modernisation_summary}</p>`;
      }
    }

  // Initialize settings form
  const fileExtensionsInput = document.getElementById('file-extensions');
  const ignorePathsInput = document.getElementById('ignore-paths');
  const supersummaryIntervalInput = document.getElementById('supersummary-interval');
  const generateFinalSummaryInput = document.getElementById('generate-final-summary');
  const generateModernisationSummaryInput = document.getElementById('generate-modernisation-summary');

  if (fileExtensionsInput) fileExtensionsInput.value = settings.fileExtensions;
  if (ignorePathsInput) ignorePathsInput.value = settings.ignorePaths;
  if (supersummaryIntervalInput) supersummaryIntervalInput.value = settings.supersummaryInterval.toString();
  if (generateFinalSummaryInput) generateFinalSummaryInput.checked = settings.generateFinalSummary;
  if (generateModernisationSummaryInput) generateModernisationSummaryInput.checked = settings.generateModernisationSummary;
});
