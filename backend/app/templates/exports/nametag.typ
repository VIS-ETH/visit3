#let data = json.decode(sys.inputs.at("data"))

#let tag-width = 90mm
#let tag-height = 54mm
#let gap = 4mm
#let columns = data.columns

#set page("a4", margin: 10mm)
#set text(font: "DejaVu Sans")

#let tag-value(tag, key) = {
  if key == "full_name" {
    tag.full_name
  } else if key == "position" {
    tag.position
  } else if key == "company" {
    tag.company
  } else {
    ""
  }
}

#let nametag-field(
  tag,
  key,
  x,
  y,
  width,
  height,
  size,
  fill,
  weight: "regular",
) = {
  place(top + left, dx: x, dy: y)[
    #block(width: width, height: height)[
      #align(center + horizon)[
        #text(size: size, fill: rgb(fill), weight: weight)[#tag-value(tag, key)]
      ]
    ]
  ]
}

#let nametag(tag) = {
  block(width: tag-width, height: tag-height)[
    #place(top + left)[
      #image(data.background_path, width: tag-width, height: tag-height, fit: "stretch")
    ]
    #nametag-field(
      tag,
      "full_name",
      10mm,
      22mm,
      70mm,
      9mm,
      18pt,
      "#111111",
      weight: "bold",
    )
    #nametag-field(tag, "position", 12mm, 32mm, 66mm, 6mm, 10pt, "#333333")
    #nametag-field(tag, "company", 12mm, 40mm, 66mm, 6mm, 9pt, "#333333")
  ]
}

#grid(
  columns: columns,
  gutter: gap,
  ..data.tags.map(nametag),
)
