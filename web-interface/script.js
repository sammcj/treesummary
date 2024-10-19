document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('config-form');
  const resultsSection = document.getElementById('results');

  if (form instanceof HTMLFormElement && resultsSection) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const formData = new FormData(form);
      const config = {
        directory: formData.get('directory') || '',
        file_extensions: (formData.get('file-extensions') || '').toString().split(',').map(ext => ext.trim()),
        ignore_paths: (formData.get('ignore-paths') || '').toString().split(',').map(path => path.trim()),
        limit: parseInt((formData.get('file-limit') || '0').toString()),
        supersummary_interval: parseInt((formData.get('supersummary-interval') || '10').toString()),
        generate_final_summary: formData.get('generate-final-summary') === 'on',
        generate_modernisation_summary: formData.get('generate-modernisation-summary') === 'on'
      };

      try {
        const response = await fetch('http://localhost:5000/analyze', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(config),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        displayResults(data);
      } catch (error) {
        console.error('Error:', error);
        alert('An error occurred during analysis. Please check the console for more details.');
      }
    });

    function displayResults(data) {
      if (resultsSection) {
        resultsSection.style.display = 'block';
      }

      // Display summaries
      const summariesDiv = document.getElementById('summaries');
      if (summariesDiv) {
        summariesDiv.innerHTML = '<h3>File Summaries</h3>';
        Object.entries(data.summaries).forEach(([file, summary]) => {
          summariesDiv.innerHTML += `<h4>${file}</h4><p>${summary.summary}</p>`;
          if (summary.modernisation_recommendations) {
            summariesDiv.innerHTML += `<h5>Modernisation Recommendations</h5><p>${summary.modernisation_recommendations}</p>`;
          }
        });
      }

      // Display supersummaries
      const supersummariesDiv = document.getElementById('supersummaries');
      if (supersummariesDiv) {
        supersummariesDiv.innerHTML = '<h3>Supersummaries</h3>';
        data.supersummaries.forEach((supersummary, index) => {
          supersummariesDiv.innerHTML += `<h4>Supersummary ${index + 1}</h4><p>${supersummary}</p>`;
        });
      }

      // Display final summary
      const finalSummaryDiv = document.getElementById('final-summary');
      if (finalSummaryDiv) {
        if (data.final_summary) {
          finalSummaryDiv.innerHTML = `<h3>Final Summary</h3><p>${data.final_summary}</p>`;
        } else {
          finalSummaryDiv.innerHTML = '';
        }
      }

      // Display modernisation summary
      const modernisationSummaryDiv = document.getElementById('modernisation-summary');
      if (modernisationSummaryDiv) {
        if (data.modernisation_summary) {
          modernisationSummaryDiv.innerHTML = `<h3>Modernisation Summary</h3><p>${data.modernisation_summary}</p>`;
        } else {
          modernisationSummaryDiv.innerHTML = '';
        }
      }
    }
  }
});
