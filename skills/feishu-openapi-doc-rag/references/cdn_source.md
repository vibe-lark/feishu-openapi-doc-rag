# CDN Source

Default JSON index location (stable CDN):

```
https://lf3-static.bytednsdoc.com/obj/eden-cn/oaleh7nupthpqbe/larkopenapidoc.json
```

This file is expected to be periodically updated. The skill workflow should:
- download to a temp file
- build `index.sqlite`
- keep a previous snapshot for daily diffs

