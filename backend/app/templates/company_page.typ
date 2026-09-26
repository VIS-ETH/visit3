#let page-width = 148.5mm
#let page-height = 210mm
#let sidebar-width = 50mm
#let content-padding = 8mm
#let sidebar-padding = 6mm
#let logo-height = 22mm
#let body-size = 8pt
#let neutral-banner = rgb("#4b5563")
#let muted = rgb("#5f6368")
#let white = rgb("#ffffff")

#let field(entry, key) = {
  let current = entry.at(key, default: none)
  if current == none { "" } else { current }
}

#let banner-color(entry) = {
  let color = field(entry, "zone_color")
  if color == "" { neutral-banner } else { rgb(color) }
}

#let sidebar-label(label) = text(
  size: 6.5pt,
  weight: "bold",
  fill: white.transparentize(20%),
  upper(label),
)

#let sidebar-row(label, value) = stack(
  spacing: 1.4mm,
  sidebar-label(label),
  text(size: 7.5pt, fill: white, value),
)

#let yes-no(value) = if value [Yes] else [No]

#let number-or-dash(value) = if value == none [-] else [#str(value)]

#let styled-run(run) = {
  let body = text(run.at("text", default: ""))
  if run.at("underline", default: false) { body = underline(body) }
  if run.at("strike", default: false) { body = strike(body) }
  if run.at("italic", default: false) { body = emph(body) }
  if run.at("bold", default: false) { body = strong(body) }
  body
}

#let description-inline(item) = if item.at("break", default: false) {
  linebreak()
} else {
  styled-run(item)
}

#let company-description(entry) = {
  for paragraph in entry.at("description_blocks", default: ()) {
    if paragraph.len() > 0 { par(paragraph.map(description-inline).join()) }
  }
}

#let company-body(entry) = {
  let brand = field(entry, "brand_name")
  let company = field(entry, "company")
  set text(font: "DejaVu Sans", size: body-size)
  set par(justify: true, leading: 0.55em, spacing: 0.9em)
  text(size: 16pt, weight: "bold", if brand == "" { company } else { brand })
  if brand != "" and brand != company {
    linebreak()
    text(size: 9pt, fill: muted, company)
  }
  v(4mm)
  company-description(entry)
}

#let company-sidebar(entry) = {
  set text(font: "DejaVu Sans")
  set par(leading: 0.45em)
  let logo = field(entry, "logo_path")
  let booth = field(entry, "booth_number")
  let contact = (field(entry, "general_email"), field(entry, "general_phone"))
    .filter(value => value != "")
  let languages = entry.at("languages", default: ())
  let industries = entry.at("industries", default: ())
  let offers = entry.at("offers", default: (:))
  let items = ()
  if logo != "" {
    items.push(block(width: 100%, height: logo-height, fill: white, inset: 2mm, radius: 1mm)[
      #align(center + horizon, image(logo, width: 100%, height: 100%, fit: "contain"))
    ])
  }
  if booth != "" {
    items.push(align(right, text(size: 16pt, weight: "bold", fill: white, booth)))
  }
  if contact.len() > 0 {
    items.push(sidebar-row("Contact", contact.join(linebreak())))
  }
  if field(entry, "website") != "" {
    items.push(sidebar-row("Website", field(entry, "website")))
  }
  if field(entry, "places_of_work") != "" {
    items.push(sidebar-row("Places of work", field(entry, "places_of_work")))
  }
  if languages.len() > 0 {
    items.push(sidebar-row("Languages", languages.join(", ")))
  }
  if industries.len() > 0 {
    items.push(sidebar-row("Areas of activity", industries.join(", ")))
  }
  items.push(line(length: 100%, stroke: 0.3mm + white))
  items.push(sidebar-row(
    "Employees",
    grid(
      columns: (1fr, auto),
      row-gutter: 1.2mm,
      [Worldwide], number-or-dash(entry.at("employee_count_worldwide", default: none)),
      [Switzerland], number-or-dash(entry.at("employee_count_switzerland", default: none)),
    ),
  ))
  items.push(grid(
    columns: (1fr, 1fr),
    column-gutter: 2mm,
    row-gutter: 3.2mm,
    sidebar-row("Internships", yes-no(offers.at("internships", default: false))),
    sidebar-row("Part-time", yes-no(offers.at("part_time", default: false))),
    sidebar-row("Theses", yes-no(offers.at("theses", default: false))),
    sidebar-row("Graduates", yes-no(offers.at("graduate_positions", default: false))),
  ))
  stack(spacing: 3.2mm, ..items)
}

#let body-width = page-width - sidebar-width - 2 * content-padding
#let body-height = page-height - 2 * content-padding
#let sidebar-inner-width = sidebar-width - 2 * sidebar-padding
#let sidebar-inner-height = page-height - 2 * sidebar-padding

#let company-page-overflows(entry) = {
  let body = measure(block(width: body-width, company-body(entry))).height
  let sidebar = measure(block(width: sidebar-inner-width, company-sidebar(entry))).height
  body > body-height or sidebar > sidebar-inner-height
}

#let company-page(entry) = block(width: page-width, height: page-height, clip: true)[
  #grid(
    columns: (1fr, sidebar-width),
    rows: page-height,
    block(width: 100%, height: 100%, inset: content-padding, clip: true, company-body(entry)),
    block(
      width: 100%,
      height: 100%,
      fill: banner-color(entry),
      inset: sidebar-padding,
      clip: true,
      company-sidebar(entry),
    ),
  )
]

#let data = sys.inputs.at("data", default: none)

#if data != none {
  let entry = json(bytes(data))
  set page(width: page-width, height: page-height, margin: 0mm)
  context [#metadata(company-page-overflows(entry)) <overflow>]
  company-page(entry)
}
