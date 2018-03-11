.PHONY:site
site:
	JEKYLL_ENV=production bundle exec jekyll build

.PHONY:serve
serve:
	JEKYLL_ENV=development bundle exec jekyll serve --verbose --watch

.PHONY:release
release: site
	cd _site; rsync -PaAXz . $(USER)@$(WEB_SERVER):$(SITE_PATH)
