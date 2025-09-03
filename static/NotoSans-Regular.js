var notoSansRegular = `
AAEAAAASAQAABAAgR0RFRrRCsIIAAAjcAAAAHEdQT1O7tr1oAAAZsAAAACBHU1VCAAAAAAAAaUwA
AAAkT1MvMtkHxIAAAFlwAAACamNtYXAAAw0gAAABMAAAAUZnYXNwAAAAEAAAAXAAAAAIZ2x5Zkjf
... (BIG BASE64 FONT DATA) ...
`; 

if (typeof window !== "undefined" && window.jspdf) {
  window.jspdf.jsPDF.API.events.push([
    "addFonts",
    function () {
      this.addFileToVFS("NotoSans-Regular.ttf", notoSansRegular);
      this.addFont("NotoSans-Regular.ttf", "NotoSans", "normal");
    },
  ]);
}
