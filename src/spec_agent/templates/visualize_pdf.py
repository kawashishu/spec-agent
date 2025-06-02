# Define HTML template
HTML_PDF_VIEWER = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>{{ title }}</title>
    <style>html,body{margin:0;height:100%;}</style>
  </head>
  <body>
    <!-- iframe allows full document scrolling -->
    <iframe
      src="{{ pdf_src }}"
      style="border:none;width:100%;height:100vh;"
      allowfullscreen
    ></iframe>
    <!-- fallback for older browsers -->
    <noscript>
      <embed src="{{ pdf_src }}" type="application/pdf" width="100%" height="100%"/>
    </noscript>
  </body>
</html>
"""