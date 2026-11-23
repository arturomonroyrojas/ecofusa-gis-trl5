<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0" 
    xmlns="http://www.opengis.net/sld" 
    xmlns:ogc="http://www.opengis.net/ogc">
  <NamedLayer>
    <Name>rondas_hidricas</Name>
    <UserStyle>
      <Title>Estilo Oficial Rondas Hidricas Fusagasuga</Title>
      <FeatureTypeStyle>
        <Rule>
          <Name>RondaHidricaProteccion</Name>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">#0284C7</CssParameter>
              <CssParameter name="fill-opacity">0.28</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#0369A1</CssParameter>
              <CssParameter name="stroke-width">1.6</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
