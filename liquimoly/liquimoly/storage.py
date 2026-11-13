from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class ForgivingManifestStaticFilesStorage(ManifestStaticFilesStorage):
    """Hashed static file names (app.3f2a1c.css) for long-term browser caching.

    * ``manifest_strict = False``: a template referencing a file that is not in
      the manifest gets the plain URL instead of a 500 error.
    * References inside third-party CSS/JS to files that do not exist (e.g.
      jazzmin's ``*.js.map`` source maps) are left untouched instead of
      aborting ``collectstatic``.
    """

    manifest_strict = False

    def hashed_name(self, name, content=None, filename=None):
        try:
            return super().hashed_name(name, content, filename)
        except ValueError:
            return name
