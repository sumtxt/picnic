# Paper Picnic

A weekly basket with the latest published research in political science. On Fridays at 2 AM UTC, we query the Crossref API for new research articles that appeared in the previous 7 days across many journals in political science and adjacent fields. [paper-picnic.com/](https://paper-picnic.com/)

The crawler lives in the `main` branch of the backend while the website is rendered from the `gh-pages` branch.

After forking the repository, you need to make some changes to the repository settings for it to function properly.

1. Go to Settings > Actions > General. Scroll down to Workflow permissions and allow workflows to read and write in the repository.

2. Go to Security > Secrets and Variables > Actions. Set `CROSSREF_EMAIL` and `OPENOPENAI_APIKEY` in as a repository secret.  The latter is used to query the OpenAI API while the former is to politely identify yourself to the Crossref API.
