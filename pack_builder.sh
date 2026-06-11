#!/bin/bash
# pack_builder.sh — CV validator gate + PDF export
# Runs cv_validator.py before exporting PDFs. Blocks if violations found.
# Usage: pack_builder.sh <pack_dir>
# Example: pack_builder.sh /home/hermes/haxjobs/packs/Spotify_Backend_Engineer/

set -euo pipefail

PACK_DIR="${1:-}"
if [ -z "$PACK_DIR" ] || [ ! -d "$PACK_DIR" ]; then
    echo "Usage: pack_builder.sh <pack_dir>"
    echo "Example: pack_builder.sh /home/hermes/haxjobs/packs/Spotify_Backend_Engineer/"
    exit 1
fi

VALIDATOR="/home/hermes/haxjobs/cv_validator.py"
PROFILE="/home/hermes/haxjobs/cv_profile.typed.json"
CHROME="/usr/bin/google-chrome"

if [ ! -f "$VALIDATOR" ]; then
    echo "ERROR: cv_validator.py not found at $VALIDATOR"
    exit 1
fi

if [ ! -f "$PROFILE" ]; then
    echo "ERROR: cv_profile.typed.json not found at $PROFILE"
    exit 1
fi

echo "=== Pack Builder ==="
echo "Pack dir: $PACK_DIR"
echo "Validator: $VALIDATOR"
echo "Profile: $PROFILE"
echo ""

# Find CV HTML file — look for Arinze_Elenasulu_*_CV.html
CV_HTML=$(find "$PACK_DIR" -maxdepth 2 -name "*_CV.html" -print | head -1)
if [ -z "$CV_HTML" ]; then
    echo "WARNING: No CV HTML found in $PACK_DIR — skipping validation"
else
    echo "Found CV: $CV_HTML"
    echo ""
    echo "── Running cv_validator.py ──"
    set +e
    python3 "$VALIDATOR" "$CV_HTML" "$PROFILE"
    VALIDATOR_EXIT=$?
    set -e

    if [ $VALIDATOR_EXIT -ne 0 ]; then
        echo ""
        echo "✗ VALIDATION FAILED — PDF export blocked."
        echo "  Fix the violations above and re-run pack_builder.sh"
        exit 1
    fi
    echo ""
    echo "✓ cv_validator.py passed — proceeding to PDF export"
fi

# ── PDF Export ──
echo ""
echo "── Exporting PDFs ──"

export_html() {
    local html_file="$1"
    local pdf_file="${html_file%.html}.pdf"
    echo "  $html_file → $pdf_file"
    "$CHROME" --headless --no-sandbox --disable-gpu --no-pdf-header-footer \
        --print-to-pdf="$pdf_file" \
        "file://$html_file" 2>/dev/null
    if [ -f "$pdf_file" ]; then
        pdf_count=$(pdfinfo "$pdf_file" 2>/dev/null | grep "Pages:" | awk '{print $2}')
        if [ -n "$pdf_count" ] && [ "$pdf_count" -gt 0 ] 2>/dev/null; then
            echo "    OK: $pdf_count pages"
        else
            echo "    OK: generated (pdfinfo not available)"
        fi
    else
        echo "    FAIL: PDF generation failed"
    fi
}

# Export CV
if [ -n "$CV_HTML" ] && [ -f "$CV_HTML" ]; then
    export_html "$CV_HTML"
fi

# Export Cover Letter
CL_HTML=$(find "$PACK_DIR" -maxdepth 2 -name "*_Cover_Letter.html" -print | head -1)
if [ -n "$CL_HTML" ] && [ -f "$CL_HTML" ]; then
    export_html "$CL_HTML"
fi

# Export Application Questions
AQ_HTML=$(find "$PACK_DIR" -maxdepth 2 -name "*_Application_Questions.html" -print | head -1)
if [ -n "$AQ_HTML" ] && [ -f "$AQ_HTML" ]; then
    export_html "$AQ_HTML"
fi

# Export Form Answers
FA_HTML=$(find "$PACK_DIR" -maxdepth 2 -name "*_Form_Answers.html" -print | head -1)
if [ -n "$FA_HTML" ] && [ -f "$FA_HTML" ]; then
    export_html "$FA_HTML"
fi

echo ""
echo "=== Pack Builder complete ==="

# ── Final scan for em dashes in PDFs ──
for pdf in "$PACK_DIR"/*.pdf "$PACK_DIR"/*/*.pdf; do
    if [ -f "$pdf" ]; then
        EM_COUNT=$(pdftotext "$pdf" - 2>/dev/null | grep -c $'\xe2\x80\x94' || echo 0)
        if [ "$EM_COUNT" -gt 0 ]; then
            echo "  ⚠ WARNING: $EM_COUNT em dash(es) found in $(basename "$pdf") — re-generate"
        fi
    fi
done
