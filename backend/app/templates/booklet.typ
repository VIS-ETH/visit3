// Visit2-style booklet layout: landscape A4 spreads, two half-pages per sheet.
//
// Inputs:
//   data.event_name        — title for the cover
//   data.pages             — list of page descriptors, each is one of:
//       { type: "pair", left_entry, right_entry }
//       { type: "with_ad", entry, ad_path }
//       { type: "leftover", entry }
//   data.intro_page_path   — optional PDF, full-bleed landscape page after the cover
//   data.blank_page_path   — optional PDF used as the right half of "leftover" pages

#let data = json.decode(sys.inputs.at("data"))

#set page("a4", flipped: true, margin: 0mm)
#set text(font: "DejaVu Sans", size: 8.5pt)
#set par(justify: true, leading: 0.55em)

#let half-width = 148.5mm
#let half-height = 210mm

#let content-padding = 8mm
#let sidebar-width = 50mm

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

#let value(entry, key) = {
  if key in entry {
    let current = entry.at(key)
    if current == none {
      ""
    } else {
      current
    }
  } else {
    ""
  }
}

#let list-text(items) = {
  if items.len() == 0 {
    "-"
  } else {
    items.join(", ")
  }
}

#let zone-color(entry) = {
  let raw = value(entry, "zone_color")
  if raw == "" or raw == none {
    rgb("#1f2933")
  } else {
    rgb(raw)
  }
}

#let sidebar-section-divider() = [
  #v(2mm)
  #line(length: 100%, stroke: 0.3mm + rgb("#ffffff"))
  #v(2mm)
]

#let sidebar-label(label) = {
  text(size: 7pt, fill: rgb("#ffffff").lighten(15%), weight: "bold", upper(label))
}

#let sidebar-value(value) = {
  text(size: 8pt, fill: rgb("#ffffff"), value)
}

#let sidebar-row(label, value-content) = {
  block(spacing: 1.4mm)[
    #sidebar-label(label) \
    #sidebar-value(value-content)
  ]
}

#let sidebar-kv(label, key_label, key_value) = {
  block(spacing: 1.2mm)[
    #grid(
      columns: (1fr, auto),
      gutter: 2mm,
      sidebar-value(key_label),
      sidebar-value(key_value),
    )
  ]
}

#let format-int(value) = {
  if value == none or value == "" {
    "-"
  } else {
    str(value)
  }
}

#let yes-no(value) = if value [Yes] else [No]

// ---------------------------------------------------------------------------
// Portrait card (one half-page)
// ---------------------------------------------------------------------------

#let portrait-card(entry) = {
  let bg = zone-color(entry)
  block(width: half-width, height: half-height)[
    #grid(
      columns: (1fr, sidebar-width),
      rows: half-height,
      // ---- Left: brand title + profile text ----
      [
        #pad(content-padding)[
          #text(size: 16pt, weight: "bold")[#value(entry, "brand_name")]
          #if value(entry, "brand_name") != value(entry, "company") [
            \
            #text(size: 9pt, fill: rgb("#5f6368"))[#value(entry, "company")]
          ]
          #v(4mm)
          #value(entry, "profile")
        ]
      ],
      // ---- Right: zone-colored sidebar ----
      [
        #block(width: 100%, height: 100%, fill: bg, inset: 6mm)[
          #align(right)[
            #text(size: 16pt, weight: "bold", fill: rgb("#ffffff"))[
              #value(entry, "booth_number")
            ]
          ]
          #v(2mm)
          #sidebar-row("Address", value(entry, "address"))
          #sidebar-row("Contact", value(entry, "contact_person"))
          #sidebar-row("Places of Work", value(entry, "places_of_work"))
          #sidebar-row("Languages", list-text(value(entry, "languages")))
          #sidebar-row(
            "Areas of Activity", list-text(value(entry, "industries"))
          )
          #sidebar-section-divider()
          #sidebar-label("Employees") \
          #sidebar-kv("worldwide", "Total worldwide", format-int(value(entry, "employees_count")))
          #sidebar-kv("ch", "Switzerland", format-int(value(entry, "employees_count_switzerland")))
          #v(1.5mm)
          #sidebar-label("Vacancies") \
          #sidebar-kv("worldwide", "Total worldwide", format-int(value(entry, "vacancies_worldwide")))
          #sidebar-kv("ch", "Switzerland", format-int(value(entry, "vacancies_switzerland")))
          #v(1.5mm)
          #sidebar-row(
            "Annual Revenue (Mio. CHF)",
            format-int(value(entry, "annual_revenue_chf_millions")),
          )
          #grid(
            columns: (1fr, 1fr, 1fr),
            gutter: 1.5mm,
            sidebar-row("Internships", yes-no("Internships" in value(entry, "offers"))),
            sidebar-row("Part-time", yes-no("Part-time roles" in value(entry, "offers"))),
            sidebar-row("Thesis", yes-no("Thesis topics" in value(entry, "offers"))),
          )
          #if value(entry, "website") != "" [
            #v(1.5mm)
            #sidebar-row("Website", value(entry, "website"))
          ]
        ]
      ],
    )
  ]
}

// Helper that fills a half-page with a single PDF image.
#let half-image(path) = block(width: half-width, height: half-height)[
  #image(path, width: 100%, height: 100%, fit: "contain")
]

#let blank-half() = block(
  width: half-width, height: half-height, fill: rgb("#fafafa")
)[]

// ---------------------------------------------------------------------------
// Cover + intro
// ---------------------------------------------------------------------------

#align(center + horizon)[
  #text(size: 36pt, weight: "bold")[#data.event_name]
  #v(6mm)
  #text(size: 16pt, fill: rgb("#5f6368"))[Booklet]
]

#if "intro_page_path" in data and data.intro_page_path != none [
  #pagebreak()
  #image(data.intro_page_path, width: 100%, height: 100%, fit: "contain")
]

// ---------------------------------------------------------------------------
// Spread pages
// ---------------------------------------------------------------------------

#let right-half-for-leftover() = {
  if "blank_page_path" in data and data.blank_page_path != none {
    half-image(data.blank_page_path)
  } else {
    blank-half()
  }
}

#for spread in data.pages {
  pagebreak()
  grid(
    columns: (half-width, half-width),
    rows: half-height,
    gutter: 0mm,
    if spread.type == "pair" {
      portrait-card(spread.left_entry)
    } else if spread.type == "with_ad" {
      portrait-card(spread.entry)
    } else if spread.type == "leftover" {
      portrait-card(spread.entry)
    },
    if spread.type == "pair" {
      portrait-card(spread.right_entry)
    } else if spread.type == "with_ad" {
      half-image(spread.ad_path)
    } else if spread.type == "leftover" {
      right-half-for-leftover()
    },
  )
}
