"use client";

import { useState } from "react";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import ListItemText from "@mui/material/ListItemText";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import DescriptionIcon from "@mui/icons-material/Description";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import TableChartIcon from "@mui/icons-material/TableChart";

import { getExportUrl } from "@/lib/api";

interface ExportSectionProps {
  jobId: string;
  filter: string;
  search: string;
}

export default function ExportSection({ jobId, filter, search }: ExportSectionProps) {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const menuOpen = Boolean(anchorEl);

  const open = (format: "xlsx" | "csv" | "pdf", scoped: boolean) => {
    window.open(getExportUrl(jobId, format, scoped ? { filter, search } : {}), "_blank");
  };

  const hasActiveScope = filter !== "all" || Boolean(search);
  const scopeDescription = hasActiveScope
    ? [filter !== "all" ? `${filter[0].toUpperCase()}${filter.slice(1)}` : null, search ? `search "${search}"` : null]
        .filter(Boolean)
        .join(", ")
    : "everything, no filter applied";

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Export Results
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
          <Button
            variant="contained"
            startIcon={<TableChartIcon />}
            endIcon={<ArrowDropDownIcon />}
            onClick={(e) => setAnchorEl(e.currentTarget)}
          >
            Download Excel (.xlsx)
          </Button>
          <Menu anchorEl={anchorEl} open={menuOpen} onClose={() => setAnchorEl(null)}>
            <MenuItem
              onClick={() => {
                open("xlsx", false);
                setAnchorEl(null);
              }}
            >
              <ListItemText
                primary="All"
                secondary="Full workbook: All / Valid / Invalid / Risky / Unknown sheets, every row"
              />
            </MenuItem>
            <MenuItem
              onClick={() => {
                open("xlsx", true);
                setAnchorEl(null);
              }}
            >
              <ListItemText primary="Validation Results" secondary={`Just the current table view (${scopeDescription})`} />
            </MenuItem>
          </Menu>

          <Button variant="outlined" startIcon={<DescriptionIcon />} onClick={() => open("csv", false)}>
            Download CSV (.csv)
          </Button>
          <Button variant="outlined" color="secondary" startIcon={<PictureAsPdfIcon />} onClick={() => open("pdf", false)}>
            Download Report (.pdf)
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
}
