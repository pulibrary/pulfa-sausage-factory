<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:mets="http://www.loc.gov/METS/"
   xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:mix="http://www.loc.gov/mix/v20" xmlns:dct="http://purl.org/dc/terms/"
   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" exclude-result-prefixes="xs xsl" version="2.0">

   <xsl:output indent="yes"/>
   <xsl:param name="title" as="xs:string"/>

   <xsl:template match="/">
      <xsl:apply-templates/>
   </xsl:template>

   <xsl:template match="folder">
      <mets:mets xmlns:mets="http://www.loc.gov/METS/" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:mix="http://www.loc.gov/mix/v20"
         xmlns:dct="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://www.loc.gov/METS/ http://www.loc.gov/standards/mets/mets.xsd" TYPE="DigitalArchivalObject">
         <xsl:attribute name="OBJID" select="@objid"/>
         <mets:metsHdr CREATEDATE="{@created}">
            <mets:metsDocumentID>
               <xsl:value-of select="@docid"/>
            </mets:metsDocumentID>
         </mets:metsHdr>
         <mets:amdSec ID="rights">
            <mets:rightsMD ID="w">
               <mets:mdWrap MDTYPE="DC">
                  <mets:xmlData>
                     <dct:accessRights>WORLD</dct:accessRights>
                  </mets:xmlData>
               </mets:mdWrap>
            </mets:rightsMD>
            <mets:rightsMD ID="po">
               <mets:mdWrap MDTYPE="DC">
                  <mets:xmlData>
                     <dct:accessRights>PRINCETON_ONLY</dct:accessRights>
                  </mets:xmlData>
               </mets:mdWrap>
            </mets:rightsMD>
         </mets:amdSec>

         <mets:amdSec ID="tech">
            <xsl:apply-templates select=".//representation[mimetype ne 'application/pdf']" mode="amdSec"/>
         </mets:amdSec>
         
         <mets:fileSec>
            <xsl:apply-templates select="current()" mode="fileSec"/>
            <xsl:apply-templates select="member" mode="fileSec"/>
         </mets:fileSec>
         
         <mets:structMap>
            <xsl:apply-templates select="current()" mode="div"/>
         </mets:structMap>
      </mets:mets>
   </xsl:template>

   <xsl:template match="representation[mimetype ne 'application/pdf']" mode="amdSec">
      <mets:techMD ID="t{generate-id(current())}">
         <mets:mdWrap MDTYPE="NISOIMG">
            <mets:xmlData>
               <mix:imageWidth>
                  <xsl:value-of select="width"/>
               </mix:imageWidth>
               <mix:imageHeight>
                  <xsl:value-of select="height"/>
               </mix:imageHeight>
            </mets:xmlData>
         </mets:mdWrap>
      </mets:techMD>
   </xsl:template>

   <xsl:template match="folder|member" mode="fileSec">
      <mets:fileGrp ID="fg{generate-id(current())}">
         <xsl:apply-templates select="representation" mode="file"/>
      </mets:fileGrp>
   </xsl:template>
   
   <xsl:template match="representation" mode="file">
      <mets:file USE="{use}" ID="f{generate-id(current())}" CHECKSUM="{checksum}" CHECKSUMTYPE="{checksum/@type}" MIMETYPE="{mimetype}" SIZE="{size}">
         <xsl:if test="mimetype ne 'application/pdf'">
            <xsl:attribute name="ADMID" select="concat('t', generate-id(current()))"/>
         </xsl:if>
         <mets:FLocat LOCTYPE="URN" xlink:href="{@urn}"/>
      </mets:file>
   </xsl:template>
   
   <xsl:template match="folder|member" mode="div">
      <xsl:variable name="order" as="xs:integer?">
         <xsl:if test="self::member">
            <xsl:value-of select="count(preceding-sibling::member) + 1"/>
         </xsl:if>
      </xsl:variable>
      <mets:div>
         <xsl:if test="$order">
            <xsl:attribute name="LABEL" select="concat('[', $order, ']')"/>
            <xsl:attribute name="ORDER" select="$order"/>
         </xsl:if>
         <xsl:if test="self::folder">
            <xsl:attribute name="LABEL" select="if ($title) then $title else '[No title]'"/>
         </xsl:if>
         <xsl:attribute name="TYPE" select="if (self::folder) then 'Folder' else 'FolderMember'"/>
         <xsl:if test="self::folder">
            <xsl:attribute name="ADMID" select="'w'"/>
         </xsl:if>
         <mets:fptr FILEID="fg{generate-id(current())}"/>
         <xsl:apply-templates select="member" mode="div"/>
      </mets:div>
   </xsl:template>
   


</xsl:stylesheet>
