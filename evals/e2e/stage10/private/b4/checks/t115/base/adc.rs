//! ADC driver for the moisture probe.
use core::{mem, ptr, slice};

pub const CHANNELS: usize = 8;
pub const START: u32 = 1 << 0;
pub const READY: u32 = 1 << 1;

/// The ADC register block (same layout as the peripheral).
#[repr(C)]
#[derive(Default)]
pub struct AdcRegs {
    pub ctrl: u32,
    pub status: u32,
    pub data: [u32; CHANNELS],
}

/// Programmable gain of the analog front end.
#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Gain {
    X1 = 0,
    X2 = 1,
    X4 = 2,
    X8 = 3,
}

pub fn read_channel(regs: &AdcRegs, ch: usize) -> u16 {
    assert!(ch < CHANNELS, "no ADC channel {ch}");
    unsafe { ptr::read_volatile(regs.data.as_ptr().add(ch)) as u16 }
}

pub fn start_conversion(regs: &mut AdcRegs) {
    let ctrl = regs.ctrl | START;
    unsafe { ptr::write_volatile(&mut regs.ctrl, ctrl) }
}

pub fn is_ready(regs: &AdcRegs) -> bool {
    unsafe { ptr::read_volatile(&regs.status) & READY != 0 }
}

pub fn clear_status(regs: &mut AdcRegs) {
    unsafe { ptr::write_volatile(&mut regs.status, 0) }
}

pub fn read_all(regs: &AdcRegs, out: &mut [u16; CHANNELS]) {
    for (ch, slot) in out.iter_mut().enumerate() {
        *slot = unsafe { ptr::read_volatile(&regs.data[ch]) } as u16;
    }
}

pub fn average(samples: &[u16]) -> u16 {
    if samples.is_empty() {
        return 0;
    }
    let mut sum = 0u32;
    for i in 0..samples.len() {
        sum += unsafe { *samples.get_unchecked(i) } as u32;
    }
    (sum / samples.len() as u32) as u16
}

/// Maps a 16-bit raw reading to a calibrated value through a 16-entry table (top 4 bits select the entry).
pub fn calibrate(raw: u16, table: &[u16; 16]) -> u16 {
    let idx = (raw >> 12) as usize;
    unsafe { *table.get_unchecked(idx) }
}

/// One sample from a capture buffer.
pub fn sample_at(buf: &[u16], idx: usize) -> u16 {
    unsafe { *buf.get_unchecked(idx) }
}

/// Raw little-endian bytes of a sample buffer, for the radio uplink.
pub fn as_bytes(samples: &[u16]) -> &[u8] {
    unsafe { slice::from_raw_parts(samples.as_ptr() as *const u8, samples.len() * mem::size_of::<u16>()) }
}

pub fn gain_from_bits(bits: u8) -> Option<Gain> {
    if bits > Gain::X8 as u8 {
        return None;
    }
    Some(unsafe { mem::transmute::<u8, Gain>(bits) })
}
