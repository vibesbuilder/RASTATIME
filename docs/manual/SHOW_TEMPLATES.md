# Show Templates

> **Where you are in the manual.** Read [Calendar](./CALENDAR.md)
> first if you have not — Show Templates are an accelerator on
> the calendar's New-Show / Edit-Show form.
>
> **What this feature replaces.** Pre-2026-05-19 the only
> shortcut for "same show settings as last week" was to copy a
> recurring show. Show Templates work for both recurring and
> one-off shows and survive after the source show is deleted.

A **Show Template** is a saved snapshot of the New-Show form's
field values. When you apply a template to a new show, every
captured field is pre-filled in one click. When you save a show
as a template, every field on the form is captured (with a few
deliberate exceptions).

Templates are **station-wide**: any Admin or Program Manager
can apply or edit any template. The settings of a weekly show
are saved once, and a colleague can stamp the same template
onto a different show.

---

## 1. Why use templates

Without templates, creating a typical recurring music show
takes about 90 seconds of form filling: name, URL, genre,
description, two hosts, background colour, text colour, show
image, autoloading playlist, "Add Autoloading Playlist?",
duration. Stations with a weekly schedule of 15-20 shows
have spent 30 minutes a week re-typing the same fields.

With templates that drops to about 5 seconds per show:

1. New Show → pick **Templates → Morning Show** in the dropdown.
2. Set the start time.
3. **Save**.

---

## 2. Creating a template

Two paths:

### 2.1 Save an existing show as a template

Open the show on the calendar → **Save as Template** in the
context menu. A dialog asks for:

| Field | Notes |
|---|---|
| **Template Name** | Unique. Defaults to the show's current name. The next New-Show dropdown will show this name. |

Click **Save**. The template is created from the current state
of the show's edit form — every field captured below is taken
*as it stands* at save time.

### 2.2 Save the New-Show form before saving the show

Inside New Show → fill in the fields you want to capture →
expand **Templates** → click **Save as Template**. Pick a
name. The template is saved without yet creating a show.

> **Operator tip.** This is useful when you want to define a
> template for "the kind of show we run on weekends" before
> you actually need to create one. You can also save partial
> templates this way — fill in just the colours and hosts you
> always use, then save.

---

## 3. Applying a template

When creating a new show:

1. New Show → expand **Templates**.
2. Pick a template from the **Select a template** dropdown.
3. Click **Apply**.
4. The form's other sections pre-fill from the template.
5. Edit any field you want to override, then **Save** as
   normal.

The template overrides every captured field. Fields you have
already filled in are *replaced* — there is no "merge". An
**Undo Apply** button appears for ten seconds to revert.

### When applying a template on an existing show

You can also re-apply a template to a show that already exists,
via **Apply Template** in the calendar context menu. This is
useful for "we changed the hosts mid-season, apply the new
template to every future show".

> **Why not auto-propagate template edits?** RASTATIME 2026-05-19
> chose a **one-way stamp** model. Editing a template never
> changes shows that were created from it. Reasons:
>
> - Predictability: an operator editing a template would have
>   no idea how many existing shows would silently change.
> - Per-show overrides: an operator who edited one show's
>   colour after applying the template would lose the override
>   if the template re-propagated.
> - Failure mode: a template edit that broke a field would
>   break every show using that template, requiring per-show
>   cleanup.
>
> If you need to mass-update existing shows, use **Apply
> Template** on each (or the **Bulk Actions** menu — see
> [Calendar](./CALENDAR.md) §8). See ARCHITECTURE §23.16 for
> the full decision log.

### When applying a template to an Edit-Instance form

You cannot. RASTATIME 2026-05-19 suppresses the **Templates**
section in the Edit-Instance dialog (one instance of a
recurring show). Re-stamping a single instance would either
silently propagate to siblings (violates the one-way stamp
model) or have no effect on them (which would mislead the
operator).

If you need to override one instance, edit its fields directly
without using the template path.

---

## 4. What a template captures

These fields are saved in the template's JSONB snapshot:

| Group | Fields |
|---|---|
| **Identity** | Show name (used as the default for next New-Show), URL, genre, description |
| **Visuals** | Background colour, text colour, show image reference |
| **Duration** | Default length |
| **Repeats** | Repeat type, repeat days, end-date / no-end flag |
| **Recording** | Record enabled (yes/no) |
| **Autoloading playlist** | Playlist ID, intro playlist ID, outro playlist ID, "repeat until full" flag |
| **Auth** | Host usernames (NOT the per-show live-stream password — see below) |
| **Show DJ source** | Per-show live-stream allowed (yes/no) |

### What a template does NOT capture

Deliberately excluded:

| Field | Reason |
|---|---|
| **Start date / start time** | Per-use; the template is reusable across many start times. |
| **Live-stream password** | Security — a saved template should not carry credentials. The operator sets the password per show. |
| **Per-instance descriptions** | Instance-specific (e.g. "this week's guest is X"). |

> **How it works under the hood.** Templates live in the
> `cc_show_template` table (`id`, `name UNIQUE`, `template_data
> JSONB`, `created_at`, `updated_at`). The PHP service
> `Application_Service_ShowTemplateService` owns CRUD via 5
> JSON actions registered on `ScheduleController`. Apply-time
> the template's JSONB is folded into the array consumed by
> `populateForm()`. Schema drift is tolerated: a template
> missing a field at apply time falls back to the form
> default; a template carrying an unknown field is silently
> ignored.

### Show image stored as a reference, not a copy

If a template captures a show image, only the path to the
existing image file is saved — not a copy of the image bytes.
This was a deliberate trade-off:

- Pro: storage usage stays flat regardless of how many shows
  are stamped from a template.
- Con: deleting the source image (e.g. from
  `C:\rastatime\media\<owner>\.../show-logo.png`) leaves the
  template (and every show stamped from it) without an image.

If you delete or move a show image, re-upload it under the
same path, or re-save the template with a current image.

---

## 5. Renaming or deleting a template

Two routes:

### 5.1 From the Settings → Show Templates page

Settings → **Show Templates** opens a list of every template
on the station. Each row has:

| Column | Action |
|---|---|
| **Name** | Click to rename. The new name must be unique. |
| **Last updated** | Sortable. |
| **Used by** | A count of shows currently using this template (informational; templates do not "track" usage retroactively). |
| **Edit** | Open the template's JSON in a read-only viewer — useful for the technical reader to verify what was captured. |
| **Delete** | Confirms, then drops the template. Shows stamped from it are unaffected. |

> **Operator tip.** The Settings page is the easiest way to
> rename a template after a typo. Renaming via the New-Show
> form's **Save as Template** with the same name as an
> existing template prompts for **Overwrite?** — easy to do
> by accident.

### 5.2 From the New-Show / Edit-Show dialog

Expand **Templates** → pick the template in the dropdown → an
**Edit** icon appears next to the dropdown → opens the
rename / delete dialog inline.

---

## 6. Overwrite-on-duplicate behaviour

If you save a new template with a name that already exists,
the save request returns a 409 Conflict-style response and
the UI prompts:

> **A template named "Morning Show" already exists. Overwrite?**

| Click | Effect |
|---|---|
| **Cancel** | Discard the new template; the existing one is unchanged. |
| **Overwrite** | Replace the existing template's `template_data` with the current form values. `updated_at` is bumped. The name is unchanged. |

> **How it works under the hood.** The API endpoint
> `Schedule/save-show-template` returns `{ "conflict": true,
> "template_id": <existing> }` instead of `{ "ok": true }` on
> name collision. The JS in `add-show.js` shows the prompt and
> reposts with `overwrite=true` if the operator confirmed.
> Without overwrite the existing row stays intact.

---

## 7. Worked example: a weekly morning show

A station runs **Morning Show** Mon-Fri 07:00–10:00 with:

- Hosts: Anna + Ben
- Background colour: dark blue
- Text colour: white
- Show image: morning-show-logo.png
- Autoloading playlist: "Morning Playlist" with intro + outro
- Recording enabled
- Live-stream allowed for guest-host Wednesdays

**First time:**

1. Create the Monday occurrence: New Show, fill all fields,
   save.
2. Open the Monday show → **Save as Template** → name it
   `Morning Show`.

**For Tuesday, Wednesday, Thursday, Friday:**

1. New Show → Templates → **Morning Show** → Apply.
2. Set start date.
3. Save.

**Or for a recurring show definition (preferred):**

1. New Show → Templates → **Morning Show** → Apply.
2. Set start date.
3. Tick **Repeats** → Weekly → Mon, Tue, Wed, Thu, Fri.
4. Save.

This generates all five days as instances of one recurring
show definition. Editing the show definition later changes
all five.

---

## 8. Frequently-asked

### "Can I create a template that has only the colours, no other fields?"

Yes. Open a blank New-Show form, fill in only background and
text colour, then **Save as Template** with a name like
`Colour: Dark blue`. When applied, only those two fields are
overridden; everything else stays at form defaults.

### "Can a DJ save / apply templates?"

No. Templates live in the show dialog, and shows are
created and edited by Program Managers and Admins only; they
also save, rename and delete templates, in the dialog and on
the overview page Settings → Show Templates.

### "I changed the host list on the template — why are existing shows unchanged?"

By design — see §3, "Why not auto-propagate template edits?".
Use **Apply Template** on each existing show that should
inherit the change.

### "Can I export a template to use on another station?"

Not via the UI. The technical workaround:
`SELECT * FROM cc_show_template WHERE name = 'Morning Show'`
on the source station, then `INSERT … ON CONFLICT DO NOTHING`
on the target. Note that referenced playlist IDs and image
paths will not resolve across stations.

### "What is the maximum number of templates?"

There is no hard limit. The **Templates** dropdown in the
New-Show form scrolls if there are more than 20 entries.
Stations with 50+ templates may want to use a name-prefix
convention (`Music — Pop`, `Music — Jazz`, `News — Hourly`).

---

## Where to go next

* [Calendar](./CALENDAR.md) — where templates are applied.
* [Autoloading Playlists](./AUTOLOADING_PLAYLISTS.md) — the
  most common reason templates are useful.
* [Settings](./SETTINGS.md) — tour of every Settings sub-page
  including Show Templates.
