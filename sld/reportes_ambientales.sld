<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0" 
    xmlns="http://www.opengis.net/sld" 
    xmlns:ogc="http://www.opengis.net/ogc">
  <NamedLayer>
    <Name>reportes_ambientales</Name>
    <UserStyle>
      <Title>Semaforo Reportes EcoFusa</Title>
      <FeatureTypeStyle>
        <Rule>
          <Name>CriticoRonda</Name>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>en_ronda_hidrica</ogc:PropertyName>
              <ogc:Literal>true</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <PointSymbolizer>
            <Graphic>
              <Mark>
                <WellKnownName>circle</WellKnownName>
                <Fill><CssParameter name="fill">#DC2626</CssParameter></Fill>
                <Stroke><CssParameter name="stroke">#FFFFFF</CssParameter><CssParameter name="stroke-width">1.8</CssParameter></Stroke>
              </Mark>
              <Size>12</Size>
            </Graphic>
          </PointSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
