// Visit2-style nametag layout: 90mm x 54mm tags, two per row in A4 portrait.
// Inputs:
//   data.background_path  — full nametag background image
//   data.columns           — caller-overridable column count (defaults to 2)
//   data.tags              — list of {full_name, position, company}

#let data = json.decode(sys.inputs.at("data"))

#let tag-width = 90mm
#let tag-height = 54mm
#let tag-gap = 10mm
#let columns = data.columns

#set page("a4", margin: 8mm)
#set text(font: "DejaVu Sans")

#let nametag(tag) = {
  block(
    width: tag-width,
    height: tag-height,
    stroke: 0.3pt + rgb("#222222"),
  )[
    #place(top + left)[
      #image(data.background_path, width: tag-width, height: tag-height)
    ]
    #place(top + left, dx: 6mm, dy: 18.5mm)[
      #block(width: tag-width - 8mm)[
        #set text(font: "DejaVu Serif", size: 18pt, weight: "bold")
        #set par(leading: 4pt)
        #tag.full_name
      ]
    ]
    #place(top + left, dx: 6mm, dy: 40mm)[
      #block(width: tag-width - 9mm)[
        #set text(font: "DejaVu Sans", size: 11pt)
        #set par(leading: 3pt)
        #tag.position \
        #text(weight: "bold")[#tag.company]
      ]
    ]
  ]
}

#grid(
  columns: columns,
  column-gutter: tag-gap,
  row-gutter: tag-gap,
  ..data.tags.map(nametag),
)
