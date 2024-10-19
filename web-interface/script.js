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
  const startAnalysisBtn = document.createElement('button');
  startAnalysisBtn.textContent = 'Start Analysis';
  startAnalysisBtn.id = 'start-analysis-btn';
  document.body.appendChild(startAnalysisBtn);

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
  startAnalysisBtn.addEventListener('click', analyzeProject);

  document.addEventListener('dragover', onDragOver);
  document.addEventListener('drop', onDrop);

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
              item.draggable = true;
              item.dataset.path = fullPath;
              item.addEventListener('dragstart', onDragStart);
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
    const bucket = createBucketElement();
    bucketContainer.appendChild(bucket);
  }

  function createBucketElement() {
    const bucket = document.createElement('div');
    bucket.className = 'bucket';
    bucket.innerHTML = '<h3>New Bucket</h3><ul></ul>';
    bucket.addEventListener('dragover', onDragOver);
    bucket.addEventListener('drop', onDrop);
      return bucket;
    }

  function onDragOver(event) {
    event.preventDefault();
  }

  function onDrop(event) {
    event.preventDefault();
    if (!event.dataTransfer) return;
    const path = event.dataTransfer.getData('text');
    let targetBucket = event.target.closest('.bucket');

    if (!targetBucket) {
      targetBucket = createBucketElement();
      bucketContainer.appendChild(targetBucket);
    }

    const ul = targetBucket.querySelector('ul');
    if (ul) {
      const item = createBucketItem(path);
      ul.appendChild(item);
      resizeBucket(targetBucket);
    }
  }

  function createBucketItem(path) {
      const item = document.createElement('li');
      item.textContent = path;
      const removeBtn = document.createElement('span');
      removeBtn.textContent = '×';
      removeBtn.className = 'remove-item';
      removeBtn.addEventListener('click', () => {
        item.remove();
        resizeBucket(item.closest('.bucket'));
      });
      item.appendChild(removeBtn);
    return item;
  }

  function resizeBucket(bucket) {
    const ul = bucket.querySelector('ul');
    if (ul) {
      const items = ul.children;
      if (items.length > 10) {
        ul.classList.add('scrollable');
        const prevBtn = bucket.querySelector('.prev-btn') || createNavButton('←', 'prev-btn');
        const nextBtn = bucket.querySelector('.next-btn') || createNavButton('→', 'next-btn');
        bucket.appendChild(prevBtn);
        bucket.appendChild(nextBtn);
      } else {
        ul.classList.remove('scrollable');
        bucket.querySelector('.prev-btn')?.remove();
        bucket.querySelector('.next-btn')?.remove();
      }
    }
  }

  function createNavButton(text, className) {
    const btn = document.createElement('button');
    btn.textContent = text;
    btn.className = className;
    btn.addEventListener('click', () => {
      const ul = btn.parentElement.querySelector('ul');
      if (ul) {
        ul.scrollLeft += className === 'next-btn' ? 100 : -100;
      }
    });
    return btn;
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
              files: Array.from(bucket.querySelectorAll('li')).map(li => li.textContent.replace('×', '').trim())
            };
        });

      // Show progress indicator
      const progressIndicator = document.createElement('div');
      progressIndicator.id = 'progress-indicator';
      progressIndicator.textContent = 'Processing...';
      document.body.appendChild(progressIndicator);

      fetch('http://localhost:5000/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ buckets, settings }),
      })
        .then(response => response.json())
          .then(data => {
            // Remove progress indicator
            progressIndicator.remove();
            displayResults(data);
          })
          .catch(error => {
            console.error('Error:', error);
            progressIndicator.remove();
            alert('An error occurred during analysis. Please check the console for more details.');
          });
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
                    <div class="markdown-content">${marked(summary.summary)}</div>
                    ${summary.modernisation_recommendations ? `<h5>Modernisation Recommendations</h5><div class="markdown-content">${marked(summary.modernisation_recommendations)}</div>` : ''}
                `;
            }

          if (bucket.supersummary) {
              bucketDiv.innerHTML += `<h4>Bucket Supersummary</h4><div class="markdown-content">${marked(bucket.supersummary)}</div>`;
            }

          resultsContainer.appendChild(bucketDiv);
        }

      if (data.final_summary) {
          resultsContainer.innerHTML += `<h3>Final Summary</h3><div class="markdown-content">${marked(data.final_summary)}</div>`;
        }

      if (data.modernisation_summary) {
          resultsContainer.innerHTML += `<h3>Modernisation Summary</h3><div class="markdown-content">${marked(data.modernisation_summary)}</div>`;
        }

      // Render MermaidJS diagrams
      mermaid.init(undefined, document.querySelectorAll('.mermaid'));
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
