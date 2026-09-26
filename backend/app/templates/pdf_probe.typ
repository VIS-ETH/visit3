#let source = sys.inputs.at("source")
#let page-number = int(sys.inputs.at("page"))
#let probe = image(source, page: page-number)

#context {
  let size = measure(probe)
  [#metadata((width: size.width.mm(), height: size.height.mm())) <size>]
}
