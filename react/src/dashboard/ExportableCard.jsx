import { useRef } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';

function sanitizeExportFileName(value) {
  return String(value || 'chart')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'chart';
}

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function ExportableCard({
  children,
  className = '',
  style,
  exportTitle = 'Chart',
  exportFileName = '',
}) {
  const cardRef = useRef(null);

  const handleExportPdf = () => {
    const sourceCard = cardRef.current;
    if (!sourceCard || typeof window === 'undefined') {
      return;
    }

    const exportTarget = sourceCard.querySelector('[data-export-target="true"]')
      || sourceCard.querySelector('svg[role="img"]')
      || sourceCard.querySelector('svg')
      || sourceCard;
    const exportRect = exportTarget.getBoundingClientRect();
    const viewBox = exportTarget.tagName.toLowerCase() === 'svg'
      ? exportTarget.getAttribute('viewBox')
      : null;
    const viewBoxParts = viewBox ? viewBox.split(/\s+/).map(Number) : [];
    const exportWidthPx = Math.max(
      320,
      Math.round(exportRect.width || exportTarget.clientWidth || viewBoxParts[2] || 800)
    );
    const exportHeightPx = Math.max(
      220,
      Math.round(exportRect.height || exportTarget.clientHeight || viewBoxParts[3] || 500)
    );
    const exportWidthPt = Math.round(exportWidthPx * 0.75);
    const exportHeightPt = Math.round(exportHeightPx * 0.75);

    const printWindow = window.open('', '_blank', 'width=1440,height=1024');
    if (!printWindow) {
      return;
    }

    const clonedTarget = exportTarget.cloneNode(true);
    clonedTarget.querySelectorAll('[data-export-control="true"]').forEach((node) => node.remove());
    const rootStyles = window.getComputedStyle(document.documentElement);
    const resolvedMarkup = clonedTarget.outerHTML.replace(/var\((--[^),\s]+)(?:,[^)]+)?\)/g, (_, variableName) => {
      const value = rootStyles.getPropertyValue(variableName).trim();
      return value || '#000000';
    });

    const styleMarkup = Array.from(document.querySelectorAll('style, link[rel="stylesheet"]'))
      .map((node) => node.outerHTML)
      .join('\n');
    const theme = document.documentElement.dataset.theme || 'light';
    const themeMode = document.documentElement.dataset.themeMode || theme;
    const documentTitle = exportFileName || sanitizeExportFileName(exportTitle);

    printWindow.document.open();
    printWindow.document.write(`
      <!doctype html>
      <html data-theme="${escapeHtml(theme)}" data-theme-mode="${escapeHtml(themeMode)}">
        <head>
          <meta charset="utf-8" />
          <title>${escapeHtml(documentTitle)}</title>
          ${styleMarkup}
          <style>
            body {
              margin: 0;
              background: #ffffff;
            }

            .export-print-shell {
              width: ${exportWidthPx}px;
              margin: 0 auto;
            }

            [data-export-control="true"] {
              display: none !important;
            }

            .export-print-shell > svg {
              display: block;
              width: ${exportWidthPx}px;
              height: ${exportHeightPx}px;
            }

            @page {
              size: ${exportWidthPt}pt ${exportHeightPt}pt;
              margin: 0;
            }
          </style>
        </head>
        <body>
          <div class="export-print-shell">${resolvedMarkup}</div>
        </body>
      </html>
    `);
    printWindow.document.close();

    const triggerPrint = () => {
      printWindow.focus();
      printWindow.print();
    };

    printWindow.addEventListener('afterprint', () => {
      printWindow.close();
    }, { once: true });

    printWindow.addEventListener('load', () => {
      window.setTimeout(triggerPrint, 250);
    }, { once: true });
  };

  return (
    <div ref={cardRef} className={className} style={style}>
      <Card className="exportable-card">
        <div className="exportable-card__actions" data-export-control="true">
          <Button
            type="button"
            label="PDF"
            icon="pi pi-file-pdf"
            severity="secondary"
            text
            size="small"
            onClick={handleExportPdf}
          />
        </div>
        {children}
      </Card>
    </div>
  );
}
