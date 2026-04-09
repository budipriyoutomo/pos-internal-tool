# core/report_generator.py
import datetime
from pathlib import Path
from config.settings import settings

class ReportGenerator:
    def __init__(self):
        self.reports_dir = settings.REPORTS_DIR
    
    def generate(self, outlet, currentdate, transactions, dine_in, takeaway):
        """
        Generate report dengan format original
        
        Args:
            outlet: Outlet code
            currentdate: Date string (YYYY-MM-DD)
            transactions: List of transaction summaries (bsum_trans)
            dine_in: List of dine-in items (bsum_menu with salemode=1)
            takeaway: List of takeaway items (bsum_menu with salemode=2)
        """
        # Parse transaction data (bsum_trans)
        disc = 0
        trans = 0
        service = 0
        tax = 0
        summary = ""
        outletcode = outlet
        outletname = outlet
        
        if transactions and len(transactions) > 0:
            x = transactions[-1]  # ambil data terakhir 

            summary = str(x.get("AmountSummary", ""))
            disc = int(x.get("Disc", 0))
            trans = float(x.get("AmountTransaksi", 0))
            service = int(x.get("AmountService", 0))
            tax = int(x.get("Tax", 0))
            outletcode = str(x.get("OutletCode", outlet))
            outletname = str(x.get("OutletName", outlet))
        
        # Create filename
        filename = self.reports_dir / f"{outlet}_{currentdate}.txt"
        
        # Generate report dengan format original
        with open(filename, 'w', encoding='utf-8') as f:
            # Header
            f.write("Consolidate Sale".center(35))
            
            MONTHS = [
                "January","February","March","April","May","June",
                "July","August","September","October","November","December"
            ]

            date_obj = datetime.datetime.strptime(currentdate, '%Y-%m-%d')
            currentdate_head = f"{date_obj.day} {MONTHS[date_obj.month-1]} {date_obj.year}"
            
            endtime = "End Time " + datetime.datetime.now().strftime('%H:%M:%S')
            
            f.write("\n" + currentdate_head.center(35) + "\n")
            f.write(endtime.center(35) + "\n")
            f.write(("Shop:" + outletname).center(35))
            f.write("\n" + outletcode + ":" + outletname)
            
            # Dine In section
            f.write("\nDine In\n")
            totaldine = 0
            countdine = 0
            
            for y in dine_in: 

                a = str(y.get("Group", ""))[0:14]
                b = str(int(y.get("TotalQty", 0)))
                c = str(int(y.get("AmountMenu", 0)))

                totaldine += int(y.get("AmountMenu", 0))
                countdine += int(y.get("TotalQty", 0))
                
                d = a.ljust(15) + b.center(10) + c.rjust(10) + " \n"
                f.write(d)
            
            f.write("Sub Total " + str(int(totaldine)).rjust(25))
            f.write("\nDiscount" + str(disc).rjust(27))
            f.write("\nTotal Dine In :" + str(int(countdine)).center(10) + str(int(totaldine - disc)).rjust(10))
            
            # Take Away section
            f.write("\n\nTake Away \n")
            totaltake = 0
            counttake = 0
            
            for z in takeaway:
                a = str(z.get("Group", ""))[0:14]
                b = str(int(z.get("TotalQty", 0)))
                c = str(int(z.get("AmountMenu", 0)))

                totaltake += int(z.get("AmountMenu", 0))
                counttake += int(z.get("TotalQty", 0))

                d = a.ljust(15) + b.center(10) + c.rjust(10) + " \n"
                f.write(d)
            
            f.write("Total Take Away : " + str(int(counttake)).center(3) + str(int(totaltake)).rjust(14))
            
            # Summary
            f.write("\n\nSub Total " + str(int((totaldine + totaltake))).rjust(25))
            f.write("\nDiscount" + str(int(disc)).rjust(27))
            
            # Perbaikan perhitungan sub total (sesuai original)
            total_all = totaldine + totaltake
            f.write("\nSub Total : " + str(int((countdine + counttake))).center(15) + str(int(total_all - disc)).rjust(8))
            
            # Footer
            f.write("\n\n" + outletcode + ":" + str(outletname[0:18]) + summary.rjust(13))
            f.write("\nDiscount".ljust(25) + str(disc).rjust(11))
            f.write("\nSub Total".ljust(25) + str(trans).rjust(11))
            f.write("\nSVC".ljust(25) + str(service).rjust(11))
            f.write("\nPb1".ljust(25) + str(tax).rjust(11))
            f.write("\n\nTotal Sales" + str(int(trans + service + tax)).rjust(24))
        
        return str(filename)