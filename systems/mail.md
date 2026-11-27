# Mail (cooperation mailbox)

Agents work with the cooperation mailbox through the `mail-cooperation` MCP server. It never sends mail: it creates drafts, and a human reviews and sends them from a mail client.

## What agents can do

- Create drafts: new messages, replies, reply-all, forwards (`create_draft`).
- Change their own drafts (`update_draft`) and delete them (`delete_draft`). Drafts saved by a mail client cannot be changed or deleted.
- Attach files: `create_draft` returns an `upload_url`. POST each file to it as `multipart/form-data` with the field `file`:

  ```sh
  curl -s -X POST -F "file=@$HOME/Downloads/<file>" "<upload_url>"
  ```

## Formatting

Every draft gets an HTML body (`body_html`) in **Verdana 10pt**, plus a plain-text `body_text` with the same content:

```html
<div style="font-family: Verdana, sans-serif; font-size: 10pt;">
  <p>Dobrý den,</p>
  <p>...</p>
</div>
```

Use `<p>` for paragraphs and `<br>` for line breaks inside one block (e.g. a signature). Do not set other fonts or sizes.
